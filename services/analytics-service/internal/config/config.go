package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	ServerPort    string
	DatabaseURL   string
	RedisURL      string
	RedisPort     string
	StreamName    string
	ConsumerGroup string
	ConsumerName  string
}

func Load() (*Config, error) {
	_ = godotenv.Load()

	return &Config{
		ServerPort:    getEnv("SERVER_PORT", "8081"),
		DatabaseURL:   getEnv("DATABASE_URL", "postgres://localhost:5432/analytics"),
		RedisURL:      getEnv("REDIS_URL", "localhost"),
		RedisPort:     getEnv("REDIS_PORT", "6379"),
		StreamName:    getEnv("STREAM_NAME", "linkpulse:events"),
		ConsumerGroup: getEnv("CONSUMER_GROUP", "analytics-service"),
		ConsumerName:  getEnv("CONSUMER_NAME", "consumer-1"),
	}, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
