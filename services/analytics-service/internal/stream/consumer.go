package stream

import (
	"context"
	"encoding/json"
	"fmt"
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

func (c *Consumer) processMessage(ctx context.Context, msg redis.XMessage) {
	eventType, ok := msg.Values["type"].(string)
	if !ok {
		c.log.Warn().Str("id", msg.ID).Msg("Message missing type field")
		c.ack(ctx, msg.ID)
		return
	}

	if eventType != "url.accessed" {
		c.ack(ctx, msg.ID)
		return
	}

	payloadStr, ok := msg.Values["payload"].(string)
	if !ok {
		c.log.Warn().Str("id", msg.ID).Msg("Message missing payload field")
		c.ack(ctx, msg.ID)
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal([]byte(payloadStr), &payload); err != nil {
		c.log.Error().Err(err).Str("id", msg.ID).Msg("Failed to parse payload")
		c.ack(ctx, msg.ID)
		return
	}

	click := c.mapToClickEvent(payload)

	if err := c.clickRepo.InsertClick(ctx, click); err != nil {
		c.log.Error().Err(err).Str("url_code", click.URLCode).Msg("Failed to insert click")
		return
	}

	c.wsHub.Broadcast(click)
	c.ack(ctx, msg.ID)

	c.log.Debug().Str("url_code", click.URLCode).Msg("Processed click event")
}

func (c *Consumer) mapToClickEvent(payload map[string]interface{}) *domain.ClickEvent {
	click := &domain.ClickEvent{
		ClickedAt: time.Now().UTC(),
	}

	if v, ok := payload["short_code"].(string); ok {
		click.URLCode = v
	}
	if v, ok := payload["ip_address"].(string); ok {
		click.IPHash = hashIP(v)
	}
	if v, ok := payload["user_agent"].(string); ok {
		click.Browser, click.OS, click.DeviceType = parseUserAgent(v)
	}
	if v, ok := payload["referrer"].(string); ok {
		click.ReferrerDomain = extractDomain(v)
	}

	return click
}

func (c *Consumer) ack(ctx context.Context, messageID string) {
	c.redis.XAck(ctx, streamName, consumerGroup, messageID)
}

func hashIP(ip string) string {
	return fmt.Sprintf("%x", ip)[:16]
}

func parseUserAgent(ua string) (browser, os, deviceType string) {
	return "Unknown", "Unknown", "desktop"
}

func extractDomain(referrer string) string {
	if referrer == "" {
		return ""
	}
	return referrer
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
