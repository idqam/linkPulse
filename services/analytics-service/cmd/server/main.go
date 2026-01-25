package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/linkpulse/analytics-service/internal/config"
	"github.com/linkpulse/analytics-service/internal/handlers"
	"github.com/linkpulse/analytics-service/internal/repository"
	"github.com/linkpulse/analytics-service/internal/services"
	"github.com/linkpulse/analytics-service/internal/stream"
	"github.com/linkpulse/analytics-service/pkg/logger"
)

func main() {
	log := logger.New()

	cfg, err := config.Load()
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to load configuration")
	}

	db, err := repository.NewPostgresConnection(cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to database")
	}
	defer db.Close()

	redisClient, err := stream.NewRedisClient(cfg.RedisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to Redis")
	}
	defer redisClient.Close()

	clickRepo := repository.NewClickRepository(db)
	analyticsService := services.NewAnalyticsService(clickRepo)
	wsHub := handlers.NewWebSocketHub()

	consumer := stream.NewConsumer(redisClient, clickRepo, wsHub, log)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go consumer.Start(ctx)
	go wsHub.Run()

	router := handlers.NewRouter(analyticsService, wsHub, log)
	server := handlers.NewServer(cfg.ServerPort, router)

	go func() {
		log.Info().Str("port", cfg.ServerPort).Msg("Starting analytics service")
		if err := server.Start(); err != nil {
			log.Fatal().Err(err).Msg("Server failed to start")
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info().Msg("Shutting down server...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Error().Err(err).Msg("Server forced to shutdown")
	}

	cancel()
	log.Info().Msg("Analytics service stopped")
}
