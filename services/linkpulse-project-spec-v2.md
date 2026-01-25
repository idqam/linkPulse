# LinkPulse: Production-Grade URL Shortener

**Timeline:** 1 Month (4 Sprints)  
**Stack:** Python FastAPI + Elixir Phoenix + React TypeScript + AWS Free Tier  
**Goal:** Demonstrate polyglot architecture, distributed systems patterns, and infrastructure/DevOps competency

---

## Why This Project Works

Most URL shorteners on GitHub are weekend toys. This one stands out because:

1. **Polyglot architecture with clear service boundaries** — Python for API layer, Elixir for event processing, React for dashboard
2. **Production infrastructure** — Terraform, Docker, CI/CD, observability
3. **Distributed systems patterns** — Event-driven analytics via Redis Streams, caching, rate limiting
4. **Cost-conscious cloud design** — AWS free tier viable

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS INFRASTRUCTURE                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │     ALB     │  │ CloudWatch  │  │     S3      │  │     ECR     │        │
│  │   (Proxy)   │  │  (Metrics)  │  │  (Assets)   │  │  (Images)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  URL SERVICE (Py)    │  │ ANALYTICS SVC (Ex)   │  │  DASHBOARD (React)   │
│  FastAPI + SQLAlchemy│  │ Phoenix + GenStage   │  │  TypeScript + Vite   │
│                      │  │                      │  │                      │
│  • Create short URLs │  │  • Stream consumer   │  │  • Analytics charts  │
│  • Redirect + track  │  │  • Time-series agg   │  │  • URL management    │
│  • Rate limiting     │  │  • Analytics API     │  │  • Real-time updates │
│  • API key auth      │  │  • WebSocket push    │  │  • QR code display   │
└──────────┬───────────┘  └──────────┬───────────┘  └──────────────────────┘
           │                         │
           │    ┌────────────────┐   │
           └───►│ Redis Streams  │◄──┘
                │ (Event Queue)  │
                └────────────────┘
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Postgres   │  │    Redis    │  │ TimescaleDB │
│   (RDS)     │  │(ElastiCache)│  │ (Analytics) │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

## Service Responsibilities

### URL Service (Python FastAPI)

**Why Python:** Familiar from Baton, demonstrates depth. FastAPI async + Pydantic excellent for APIs.

**Responsibilities:**
- URL CRUD operations
- Redirect handling (hot path)
- API key authentication
- Rate limiting (Redis-backed)
- Publish click events to Redis Streams

**Patterns Demonstrated:**
- Repository pattern
- Dependency injection
- Middleware chain (auth, rate limiting, tracing)
- Async I/O with connection pooling
- Structured logging with correlation IDs

### Analytics Service (Elixir Phoenix)

**Why Elixir:** GenStage for backpressure-aware event processing, excellent concurrency for WebSocket connections, demonstrates polyglot capability.

**Responsibilities:**
- Consume click events from Redis Streams
- Aggregate analytics (clicks per hour, geo, referrers)
- WebSocket API for real-time dashboard updates
- REST API for analytics queries

**Patterns Demonstrated:**
- GenStage producer-consumer pipeline
- Supervision trees for fault tolerance
- ETS tables for hot data caching
- Consumer groups for scalability

### Dashboard (React TypeScript)

**Why React TS:** Your standard frontend stack, consistent with portfolio.

**Responsibilities:**
- URL management UI (create, list, delete)
- Analytics visualization (charts, tables)
- Real-time updates via WebSocket
- QR code display for URLs

**Libraries:**
- Vite for build tooling
- TanStack Query for data fetching
- Recharts or Victory for visualization
- Tailwind for styling

---

## Data Models

### Postgres (URL Service) — RDS Free Tier

**Tables:**
- `urls` — id, code, original_url, user_id, created_at, expires_at, is_active, click_count, metadata
- `users` — id, email, created_at
- `api_keys` — id, user_id, key_hash, name, rate_limit, created_at, last_used_at, is_active

**Indexes:** code (unique), user_id

### TimescaleDB (Analytics Service)

Using TimescaleDB extension on Postgres for time-series. Can run on same RDS instance or separate.

**Hypertable:** `clicks`
- url_code, clicked_at, ip_hash, country, city, device_type, browser, os, referrer_domain

**Continuous Aggregates:**
- Hourly click counts per URL
- Daily unique visitors per URL

### Redis Streams Event Schema

**Stream:** `click_events`

**Event Fields:**
- event_type, url_code, timestamp, request_id
- client_ip_hash, country, city
- device_type, browser, os
- referrer

---

## Feature Specifications

### Core Features (Must Have)

| Feature | Service | Description |
|---------|---------|-------------|
| Create short URL | Python | POST endpoint with optional custom alias |
| Redirect | Python | GET /:code → 302 redirect, publish event |
| URL metadata | Python | GET endpoint returns URL info + basic stats |
| Delete URL | Python | Soft delete |
| Click processing | Elixir | Consume from Redis Streams, enrich, store |
| Analytics API | Elixir | GET endpoint returns click stats |
| Dashboard | React | Charts, URL management, real-time updates |

### Enhanced Features (Should Have)

| Feature | Service | Description |
|---------|---------|-------------|
| API key auth | Python | Bearer token, rate limit per key |
| Rate limiting | Python | Token bucket, Redis-backed |
| Link expiration | Python | Optional expires_at, return 410 after |
| Custom aliases | Python | User-provided codes with collision check |
| QR code generation | Python | Returns PNG |
| Geographic analytics | Elixir | Country/city from IP geolocation |
| Device analytics | Elixir | Browser, OS, device breakdown |
| WebSocket updates | Elixir | Push new clicks to connected dashboards |

### Stretch Goals

| Feature | Description |
|---------|-------------|
| Bulk URL creation | Multiple URLs in single request |
| A/B redirect | Split traffic between destinations |
| Link previews | Unfurl destination metadata |
| Password protection | Optional password for sensitive links |

---

## AWS Free Tier Architecture

### Services Used

| Service | Free Tier Limit | Usage |
|---------|-----------------|-------|
| EC2 t2.micro | 750 hrs/month | App servers (or use ECS) |
| RDS Postgres | 750 hrs/month, 20GB | Primary database |
| ElastiCache Redis | 750 hrs/month | Cache + Streams |
| S3 | 5GB | Static assets, Terraform state |
| CloudWatch | Basic metrics free | Monitoring |
| ECR | 500MB/month | Container images |
| ALB | 750 hrs/month | Load balancer |

### Cost Optimization

- Single RDS instance for both URL service Postgres and TimescaleDB
- t2.micro instances sufficient for demo traffic
- Use CloudWatch instead of self-hosted Prometheus/Grafana initially
- S3 for Terraform state backend

### Deployment Options

**Option A: EC2 Direct**
- Simplest, runs Docker Compose on EC2
- Good for demos, less "production-like"

**Option B: ECS Fargate**
- More complex, truly containerized
- Better resume talking point
- Slightly higher cost but still free tier viable for low traffic

---

## Infrastructure & DevOps

### Local Development (Docker Compose)

**Containers:**
- url-service (Python)
- analytics-service (Elixir)
- dashboard (React dev server)
- postgres (with TimescaleDB extension)
- redis (with Streams support)

**Features:**
- Hot reload for all services
- Shared network
- Volume mounts for code
- Environment variable management

### Terraform Structure

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── prod/
│       └── ...
├── modules/
│   ├── networking/      # VPC, subnets, security groups
│   ├── database/        # RDS Postgres
│   ├── cache/           # ElastiCache Redis
│   ├── compute/         # EC2 or ECS
│   ├── storage/         # S3 buckets
│   └── monitoring/      # CloudWatch dashboards, alarms
└── backend.tf           # S3 state backend
```

**Modules to Implement:**
- VPC with public/private subnets
- Security groups (app, db, cache)
- RDS Postgres with TimescaleDB
- ElastiCache Redis cluster
- EC2 instances or ECS services
- ALB with target groups
- CloudWatch log groups and alarms

### CI/CD Pipeline (GitHub Actions)

**Stages:**
1. Lint and type check (Python: ruff, mypy; Elixir: credo, dialyzer; TS: eslint, tsc)
2. Unit tests per service
3. Integration tests (Docker Compose up, run tests, tear down)
4. Build Docker images
5. Push to ECR
6. Terraform plan (on PR)
7. Terraform apply + deploy (on main merge)

**Additional Workflows:**
- Security scanning (Trivy for containers)
- Dependency updates (Dependabot)
- Terraform fmt check

### Observability

**CloudWatch (Free Tier):**
- Application logs (structured JSON)
- Custom metrics via SDK
- Basic dashboards
- Alarms for error rates, latency

**Metrics to Track:**
- Request rate and latency (p50, p95, p99)
- Error rates by endpoint
- Redis Streams consumer lag
- Database connection pool usage
- Click events processed per minute

**Structured Logging:**
- Correlation IDs across services
- Request/response logging (sanitized)
- Error stack traces

### Load Testing (k6)

**Scenarios:**
- Redirect throughput (hot path)
- URL creation rate
- Dashboard WebSocket connections
- Mixed workload

**Targets:**
- Redirect: p95 < 100ms
- Create URL: p95 < 200ms
- Error rate < 1%

---

## Sprint Breakdown

### Sprint 1: Foundation (Days 1-7)

**Goal:** Both backend services running locally, basic URL shortening works

#### URL Service (Python)
- [ ] Project scaffolding (FastAPI, SQLAlchemy, Alembic)
- [ ] Database models
- [ ] Create, redirect, and get URL endpoints
- [ ] Basic pytest suite
- [ ] Dockerfile

#### Analytics Service (Elixir)
- [ ] Project scaffolding (Phoenix)
- [ ] Basic health endpoint
- [ ] Dockerfile

#### Dashboard (React)
- [ ] Vite + TypeScript setup
- [ ] Basic layout and routing
- [ ] URL list page (placeholder)
- [ ] Dockerfile for production build

#### Infrastructure
- [ ] Docker Compose for local dev
- [ ] Postgres + Redis containers
- [ ] GitHub Actions: lint + test
- [ ] README with setup instructions

---

### Sprint 2: Event Pipeline & Analytics (Days 8-14)

**Goal:** Click events flow Python → Redis Streams → Elixir → TimescaleDB

#### URL Service
- [ ] Redis Streams producer
- [ ] Publish click event on redirect
- [ ] Geo enrichment (MaxMind GeoLite2)
- [ ] Device detection (user-agent parsing)
- [ ] Rate limiting middleware

#### Analytics Service
- [ ] Redis Streams consumer (GenStage)
- [ ] TimescaleDB connection and schema
- [ ] Insert click events
- [ ] Basic analytics query endpoint
- [ ] WebSocket setup for real-time push

#### Dashboard
- [ ] Connect to analytics API
- [ ] Basic click count display
- [ ] WebSocket connection for live updates

#### Infrastructure
- [ ] Health check endpoints
- [ ] Integration test scaffolding

---

### Sprint 3: Full Features & Dashboard (Days 15-21)

**Goal:** Complete dashboard, API auth, enhanced features

#### URL Service
- [ ] API key authentication
- [ ] Custom alias support
- [ ] Link expiration
- [ ] QR code generation
- [ ] Bulk creation endpoint
- [ ] CloudWatch logging integration

#### Analytics Service
- [ ] Full analytics API (time ranges, filtering)
- [ ] Continuous aggregates in TimescaleDB
- [ ] Efficient queries for dashboard

#### Dashboard
- [ ] URL management (create, list, delete, edit)
- [ ] Analytics page with charts
  - [ ] Click time series (24h, 7d, 30d)
  - [ ] Geographic breakdown
  - [ ] Device/browser breakdown
  - [ ] Top referrers
- [ ] Real-time click stream display
- [ ] QR code modal

#### Infrastructure
- [ ] Integration test suite
- [ ] CloudWatch metrics setup

---

### Sprint 4: AWS Deployment & Polish (Days 22-30)

**Goal:** Production deployment on AWS, documentation, load testing

#### Terraform
- [ ] VPC and networking module
- [ ] RDS Postgres module
- [ ] ElastiCache Redis module
- [ ] Compute module (EC2 or ECS)
- [ ] ALB module
- [ ] S3 state backend
- [ ] Environment separation (dev/prod)

#### CI/CD
- [ ] ECR push on main
- [ ] Terraform plan on PR
- [ ] Terraform apply + deploy on merge
- [ ] Rollback capability

#### Observability
- [ ] CloudWatch dashboards
- [ ] Alarm configuration
- [ ] Log aggregation

#### Load Testing & Performance
- [ ] k6 test scripts
- [ ] Run benchmarks
- [ ] Document results and capacity

#### Documentation
- [ ] Architecture diagram (C4)
- [ ] API documentation (OpenAPI)
- [ ] Deployment guide
- [ ] Local development guide
- [ ] ADRs for key decisions

---

## Repository Structure

```
linkpulse/
├── README.md
├── docs/
│   ├── architecture/
│   │   ├── c4-diagrams.md
│   │   └── decisions/
│   │       ├── 001-service-boundaries.md
│   │       ├── 002-redis-streams-over-kafka.md
│   │       └── 003-timescaledb-for-analytics.md
│   ├── api/
│   │   └── openapi.yaml
│   └── deployment.md
│
├── services/
│   ├── url-service/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── alembic/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── analytics-service/
│   │   ├── lib/
│   │   ├── test/
│   │   ├── Dockerfile
│   │   └── mix.exs
│   │
│   └── dashboard/
│       ├── src/
│       ├── Dockerfile
│       ├── package.json
│       └── tsconfig.json
│
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.prod.yml
│   │   └── .env.example
│   └── terraform/
│       ├── modules/
│       ├── environments/
│       └── backend.tf
│
├── load-tests/
│   └── k6/
│
├── scripts/
│   ├── setup-local.sh
│   └── run-migrations.sh
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
└── Makefile
```

---

## Interview Talking Points

### System Design
- "Walk me through designing a URL shortener" — Built one end-to-end
- "How do you handle analytics at scale?" — Redis Streams, TimescaleDB, continuous aggregates

### Architecture Decisions
- "Why Redis Streams over Kafka?" — Cost-effective for this scale, simpler ops, consumer groups still available
- "Why separate services?" — Independent scaling, language-appropriate tools, fault isolation

### DevOps & Infrastructure
- "How do you deploy?" — Terraform, GitHub Actions, ECR, ECS/EC2
- "How do you monitor?" — CloudWatch logs, metrics, alarms, structured logging

### Distributed Systems
- "Eventual consistency?" — Click counts update async, dashboard reflects with small delay
- "What if analytics service dies?" — Events persist in Redis Streams, consumer resumes from offset

---

## Content Opportunities

| Type | Topics |
|------|--------|
| Twitter | "Redis Streams vs Kafka for small projects", "Why I used 3 languages for 1 project" |
| Short video | "URL shortener architecture in 60 seconds", "Terraform AWS setup speedrun" |
| Blog | "Polyglot Architecture Done Right", "Redis Streams: The Poor Man's Kafka" |
| YouTube | Build series (4 parts), "System Design: URL Shortener Deep Dive" |

---

## Success Criteria

- [ ] All services deployed on AWS
- [ ] Working demo URL shareable
- [ ] CloudWatch dashboard showing metrics
- [ ] Load test proving >500 redirects/second
- [ ] Clean repo with documentation
- [ ] 2-3 content pieces published

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Elixir learning curve | Focus on GenStage basics, use Phoenix generators |
| AWS complexity | Start with EC2 + Docker Compose, upgrade to ECS if time permits |
| Scope creep | Core features first, stretch goals are optional |
| Free tier limits | Monitor usage, stay under 750 hrs/month per service |

---

*Demonstrates: polyglot architecture, event-driven design, cloud infrastructure, Terraform IaC, containerization, and production observability.*
