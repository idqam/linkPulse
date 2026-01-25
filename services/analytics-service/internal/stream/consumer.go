package stream

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/linkpulse/analytics-service/internal/domain"
	"github.com/linkpulse/analytics-service/internal/handlers"
	"github.com/linkpulse/analytics-service/internal/repository"
)

const (
	streamName    = "linkpulse:events"
	consumerGroup = "analytics-service"
	consumerName  = "consumer-1"
)

type Consumer struct {
	redis     *redis.Client
	clickRepo *repository.ClickRepository
	wsHub     *handlers.WebSocketHub
	log       zerolog.Logger
}

func NewConsumer(redisClient *redis.Client, clickRepo *repository.ClickRepository, wsHub *handlers.WebSocketHub, log zerolog.Logger) *Consumer {
	return &Consumer{
		redis:     redisClient,
		clickRepo: clickRepo,
		wsHub:     wsHub,
		log:       log,
	}
}

func (c *Consumer) Start(ctx context.Context) {
	c.ensureConsumerGroup(ctx)

	c.log.Info().Str("stream", streamName).Msg("Starting Redis Streams consumer")

	for {
		select {
		case <-ctx.Done():
			c.log.Info().Msg("Consumer shutting down")
			return
		default:
			c.consume(ctx)
		}
	}
}

func (c *Consumer) ensureConsumerGroup(ctx context.Context) {
	err := c.redis.XGroupCreateMkStream(ctx, streamName, consumerGroup, "0").Err()
	if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		c.log.Warn().Err(err).Msg("Could not create consumer group")
	}
}

func (c *Consumer) consume(ctx context.Context) {
	streams, err := c.redis.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    consumerGroup,
		Consumer: consumerName,
		Streams:  []string{streamName, ">"},
		Count:    10,
		Block:    5 * time.Second,
	}).Result()

	if err != nil {
		if err != redis.Nil {
			c.log.Error().Err(err).Msg("Error reading from stream")
		}
		return
	}

	for _, stream := range streams {
		for _, msg := range stream.Messages {
			c.processMessage(ctx, msg)
		}
	}
}

type UrlCreatedPayload struct {
	ShortCode   string    `json:"short_code"`
	OriginalURL string    `json:"original_url"`
	UserID      *int64    `json:"user_id"`
	Timestamp   time.Time `json:"timestamp"`
}

type UrlAccessedPayload struct {
	ShortCode string    `json:"short_code"`
	IPAddress string    `json:"ip_address"`
	UserAgent string    `json:"user_agent"`
	Referrer  string    `json:"referrer"`
	Timestamp time.Time `json:"timestamp"`
}

type UrlUpdatedPayload struct {
	ShortCode string                 `json:"short_code"`
	UserID    int64                  `json:"user_id"`
	Changes   map[string]interface{} `json:"changes"`
	Timestamp time.Time              `json:"timestamp"`
}

type UrlDeletedPayload struct {
	ShortCode string    `json:"short_code"`
	UserID    int64     `json:"user_id"`
	Timestamp time.Time `json:"timestamp"`
}

type UserRegisteredPayload struct {
	UserID    int64     `json:"user_id"`
	Email     string    `json:"email"`
	Timestamp time.Time `json:"timestamp"`
}

type UserLoggedInPayload struct {
	UserID    int64     `json:"user_id"`
	IPAddress string    `json:"ip_address"`
	Timestamp time.Time `json:"timestamp"`
}

func (c *Consumer) processMessage(ctx context.Context, msg redis.XMessage) {
	eventType, ok := msg.Values["type"].(string)
	if !ok {
		c.log.Warn().Str("id", msg.ID).Msg("Message missing type field")
		c.ack(ctx, msg.ID)
		return
	}

	payloadStr, ok := msg.Values["payload"].(string)
	if !ok {
		c.log.Warn().Str("id", msg.ID).Msg("Message missing payload field")
		c.ack(ctx, msg.ID)
		return
	}

	var err error
	switch eventType {
	case "url.accessed":
		err = c.handleUrlAccessed(ctx, payloadStr)
	case "user.registered", "user.logged_in", "url.created", "url.updated", "url.deleted":
		err = c.handleSystemEvent(ctx, eventType, payloadStr)
	default:
		c.log.Debug().Str("type", eventType).Msg("Ignoring unknown event type")
	}

	if err != nil {
		c.log.Error().Err(err).Str("type", eventType).Msg("Failed to process event")
		c.ack(ctx, msg.ID)
		return
	}

	c.ack(ctx, msg.ID)
}

func (c *Consumer) handleUrlAccessed(ctx context.Context, payloadStr string) error {
	var payload UrlAccessedPayload
	if err := json.Unmarshal([]byte(payloadStr), &payload); err != nil {
		return fmt.Errorf("failed to parse url.accessed payload: %w", err)
	}

	click := c.mapToClickEvent(payload)

	if err := c.clickRepo.InsertClick(ctx, click); err != nil {
		return fmt.Errorf("failed to insert click: %w", err)
	}

	c.wsHub.Broadcast(click)
	c.log.Debug().Str("url_code", click.URLCode).Msg("Processed click event")
	return nil
}

func (c *Consumer) handleSystemEvent(ctx context.Context, eventType string, payloadStr string) error {
	var payload map[string]interface{}
	if err := json.Unmarshal([]byte(payloadStr), &payload); err != nil {
		return fmt.Errorf("failed to parse %s payload: %w", eventType, err)
	}

	var userID *int64
	if v, ok := payload["user_id"].(float64); ok {
		uid := int64(v)
		userID = &uid
	}

	occurredAt := time.Now().UTC()
	if tsStr, ok := payload["timestamp"].(string); ok {
		if t, err := time.Parse(time.RFC3339, tsStr); err == nil {
			occurredAt = t
		}
	}

	if err := c.clickRepo.InsertSystemEvent(ctx, eventType, userID, payload, occurredAt); err != nil {
		return fmt.Errorf("failed to insert system event %s: %w", eventType, err)
	}

	c.log.Info().Str("type", eventType).Msg("Processed system event")
	return nil
}

func (c *Consumer) mapToClickEvent(payload UrlAccessedPayload) *domain.ClickEvent {
	click := &domain.ClickEvent{
		URLCode:   payload.ShortCode,
		ClickedAt: payload.Timestamp,
	}

	if click.ClickedAt.IsZero() {
		click.ClickedAt = time.Now().UTC()
	}

	click.IPHash = hashIP(payload.IPAddress)
	click.Browser, click.OS, click.DeviceType = parseUserAgent(payload.UserAgent)
	click.ReferrerDomain = extractDomain(payload.Referrer)

	return click
}

func (c *Consumer) ack(ctx context.Context, messageID string) {
	if err := c.redis.XAck(ctx, streamName, consumerGroup, messageID).Err(); err != nil {
		c.log.Error().Err(err).Str("id", messageID).Msg("Failed to ACK message")
	}
}

func hashIP(ip string) string {
	if ip == "" {
		return ""
	}
	return fmt.Sprintf("%x", ip)[:16]
}

func parseUserAgent(ua string) (browser, os, deviceType string) {
	browser = "Unknown"
	os = "Unknown"
	deviceType = "desktop"

	if ua == "" {
		return
	}

	switch {
	case contains(ua, "Windows"):
		os = "Windows"
	case contains(ua, "Macintosh", "Mac OS X"):
		os = "MacOS"
	case contains(ua, "Android"):
		os = "Android"
		deviceType = "mobile"
	case contains(ua, "iPhone", "iPad"):
		os = "iOS"
		deviceType = "mobile"
	case contains(ua, "Linux"):
		os = "Linux"
	}

	switch {
	case contains(ua, "Chrome") && !contains(ua, "Edg", "OPR"):
		browser = "Chrome"
	case contains(ua, "Firefox"):
		browser = "Firefox"
	case contains(ua, "Safari") && !contains(ua, "Chrome"):
		browser = "Safari"
	case contains(ua, "Edg"):
		browser = "Edge"
	case contains(ua, "OPR", "Opera"):
		browser = "Opera"
	}

	return
}

func contains(s string, subs ...string) bool {
	lower := strings.ToLower(s)
	for _, sub := range subs {
		if strings.Contains(lower, strings.ToLower(sub)) {
			return true
		}
	}
	return false
}

func extractDomain(referrer string) string {
	if referrer == "" {
		return ""
	}
	u, err := url.Parse(referrer)
	if err != nil {
		return ""
	}
	return u.Host
}

func NewRedisClient(redisURL string) (*redis.Client, error) {
	client := redis.NewClient(&redis.Options{
		Addr: fmt.Sprintf("%s:6379", redisURL),
		DB:   0,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, err
	}

	return client, nil
}
