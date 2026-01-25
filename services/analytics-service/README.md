# Analytics Service (Go)

Real-time analytics processing service for LinkPulse URL Shortener.

## Features

- Consumes click events from Redis Streams
- Stores analytics in TimescaleDB
- REST API for analytics queries
- WebSocket for real-time dashboard updates

## Architecture

```
Redis Streams → Consumer → TimescaleDB
                    ↓
              WebSocket Hub → Dashboard
                    ↓
               REST API → Dashboard
```

## Prerequisites

- Go 1.22+
- PostgreSQL with TimescaleDB extension
- Redis 7+

## Getting Started

1. Copy environment file:
```bash
cp .env.example .env
```

2. Run database migrations:
```bash
psql $DATABASE_URL -f migrations/001_initial_schema.sql
```

3. Install dependencies:
```bash
go mod tidy
```

4. Run the service:
```bash
go run cmd/server/main.go
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/analytics/:url_code` | Get full analytics for a URL |
| GET | `/api/v1/analytics/:url_code/hourly` | Get hourly click breakdown |
| WS | `/ws` | WebSocket for real-time updates |

### Query Parameters

- `period`: Time range (`24h`, `7d`, `30d`)

## Project Structure

```
analytics-service/
├── cmd/
│   └── server/
│       └── main.go           # Entry point
├── internal/
│   ├── config/               # Configuration
│   ├── domain/               # Domain models
│   ├── handlers/             # HTTP handlers & WebSocket
│   ├── repository/           # Database access
│   ├── services/             # Business logic
│   └── stream/               # Redis Streams consumer
├── pkg/
│   └── logger/               # Logging utilities
├── migrations/               # SQL migrations
├── Dockerfile
└── go.mod
```

## Docker

Build the image:
```bash
docker build -t analytics-service .
```

Run:
```bash
docker run -p 8081:8081 --env-file .env analytics-service
```
