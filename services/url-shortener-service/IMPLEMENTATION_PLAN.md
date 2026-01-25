# LinkPulse URL Shortener - Phase 2 Implementation Plan

## Executive Summary

This document outlines the implementation strategy for URL Management (CRUD), User Authentication, Redis Streams for event ingestion, and Middleware. The goal is to create a production-quality architecture suitable for a portfolio project that demonstrates modern backend practices.

---

## 1. URL Management Endpoints (CRUD Operations)

### 1.1 What Needs to Be Implemented

| Endpoint | Method | Path | Description |
|----------|--------|------|-------------|
| Get URL Details | GET | `/api/v1/short-urls/{short_code}` | ✅ Already exists |
| List User URLs | GET | `/api/v1/short-urls` | Paginated list of user's URLs |
| Update URL | PATCH | `/api/v1/short-urls/{short_code}` | Modify expiration, redirect type, or disable |
| Delete URL | DELETE | `/api/v1/short-urls/{short_code}` | Hard delete (permanent) |
| Disable URL | POST | `/api/v1/short-urls/{short_code}/disable` | Soft delete (recoverable) |
| Enable URL | POST | `/api/v1/short-urls/{short_code}/enable` | Re-enable a disabled URL |

### 1.2 Database Schema Changes

**Add to `ShortUrl` model:**
```python
user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
```

**Add relationship:**
```python
owner: Mapped[Optional["User"]] = relationship("User", back_populates="short_urls")
```

### 1.3 New DTOs Required

**File: `app/api/v1/schema_dtos.py`**

```python
class ShortURLUpdateRequest(BaseModel):
    expires_at: Optional[datetime] = None
    redirect_type: Optional[int] = None

class ShortURLListResponse(BaseModel):
    items: list[ShortURLCreateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
```

### 1.4 Implementation Location

| Component | File Path |
|-----------|-----------|
| DTOs | `app/api/v1/schema_dtos.py` |
| Routes | `app/api/v1/routes/short_urls.py` |
| Service | `app/services/short_url_service.py` |
| Repository | `app/repositories/short_url_repo.py` |

### 1.5 Trade-offs

| Decision | Trade-off |
|----------|-----------|
| **Soft delete via `is_active` flag** | Simpler than audit tables, but doesn't preserve delete history |
| **Pagination via offset** | Simple to implement but slower on large datasets vs cursor-based |
| **PATCH for updates** | More RESTful than PUT, allows partial updates |

---

## 2. User Authentication & Authorization

### 2.1 What Needs to Be Implemented

| Feature | Description |
|---------|-------------|
| User Registration | Create account with email/password |
| User Login | Return JWT access + refresh tokens |
| Token Refresh | Exchange refresh token for new access token |
| Password Hashing | BCrypt with configurable rounds |
| Protected Routes | Decorator/dependency to require authentication |
| Ownership Verification | Users can only modify their own URLs |

### 2.2 JWT Strategy

**Access Token:**
- Short-lived (15 minutes)
- Contains: `user_id`, `email`, `role`
- Stored in memory (client-side)

**Refresh Token:**
- Long-lived (7 days)
- Contains: `user_id`, `jti` (unique token ID)
- Stored in Redis for revocation capability

### 2.3 New Files Required

| File | Purpose |
|------|---------|
| `app/core/security.py` | Password hashing, JWT creation/validation |
| `app/api/v1/routes/auth.py` | Registration, login, refresh endpoints |
| `app/services/auth_service.py` | Authentication business logic |
| `app/repositories/user_repo.py` | User database operations |
| `app/api/deps.py` | FastAPI dependencies (get_current_user) |

### 2.4 Settings Additions

**Add to `app/core/settings.py`:**
```python
JWT_SECRET_KEY: str
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
BCRYPT_ROUNDS: int = 12
```

### 2.5 Endpoints

| Endpoint | Method | Path | Auth Required |
|----------|--------|------|---------------|
| Register | POST | `/api/v1/auth/register` | No |
| Login | POST | `/api/v1/auth/login` | No |
| Refresh | POST | `/api/v1/auth/refresh` | No (refresh token in body) |
| Logout | POST | `/api/v1/auth/logout` | Yes |
| Me | GET | `/api/v1/auth/me` | Yes |

### 2.6 Trade-offs

| Decision | Trade-off |
|----------|-----------|
| **JWT over sessions** | Stateless = scalable, but harder to revoke instantly without Redis |
| **Refresh tokens in Redis** | Enables revocation but adds Redis dependency for auth |
| **BCrypt over Argon2** | More widely supported, slightly less secure than Argon2id |
| **No email verification** | Simpler for portfolio, but not production-ready |
| **No OAuth/SSO** | Reduces complexity, but limits real-world usability |

---

## 3. Redis Streams for Event Ingestion

### 3.1 What Needs to Be Implemented

Events allow decoupled processing (analytics, notifications, audit logs) without blocking the main request.

**Event Types:**

| Event | Trigger | Data |
|-------|---------|------|
| `url.created` | New short URL created | `short_code`, `user_id`, `original_url`, `timestamp` |
| `url.accessed` | Redirect occurred | `short_code`, `ip`, `user_agent`, `referrer`, `timestamp` |
| `url.updated` | URL modified | `short_code`, `user_id`, `changes`, `timestamp` |
| `url.deleted` | URL removed | `short_code`, `user_id`, `timestamp` |
| `user.registered` | New user created | `user_id`, `email`, `timestamp` |
| `user.logged_in` | Successful login | `user_id`, `ip`, `timestamp` |

### 3.2 Redis Streams Architecture

```
Producer (FastAPI) → Redis Stream (linkpulse:events) → Consumer (Background Worker)
```

**Why Redis Streams over Pub/Sub:**
- Persistence: Messages survive restarts
- Consumer Groups: Multiple workers can share load
- Acknowledgment: Messages can be re-processed if worker fails
- Backpressure: Producers don't wait for consumers

### 3.3 New Files Required

| File | Purpose |
|------|---------|
| `app/events/publisher.py` | Publish events to Redis Stream |
| `app/events/schemas.py` | Pydantic models for event payloads |
| `app/events/constants.py` | Stream names, event type constants |

### 3.4 Publisher Implementation Approach

```python
class EventPublisher:
    def __init__(self, redis: RedisSingleton):
        self.redis = redis.get_instance()
        self.stream_name = "linkpulse:events"

    async def publish(self, event_type: str, payload: dict):
        event = {
            "type": event_type,
            "payload": json.dumps(payload),
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis.xadd(self.stream_name, event)
```

### 3.5 Where Events Are Published

| Location | Event |
|----------|-------|
| `ShortUrlService.create_short_url()` | `url.created` |
| `redirect.py` (after redirect) | `url.accessed` |
| `ShortUrlService.update_short_url()` | `url.updated` |
| `ShortUrlService.delete_short_url()` | `url.deleted` |
| `AuthService.register()` | `user.registered` |
| `AuthService.login()` | `user.logged_in` |

### 3.6 Trade-offs

| Decision | Trade-off |
|----------|-----------|
| **Redis Streams over Kafka** | Much simpler setup, sufficient for portfolio scale, but less durable |
| **Fire-and-forget publishing** | Faster responses, but events could be lost on Redis failure |
| **Single stream** | Simple routing, but all consumers see all events |
| **No consumer in this service** | Events published but not consumed here (assumes separate analytics service) |

---

## 4. Middleware Implementation

### 4.1 What Needs to Be Implemented

| Middleware | Purpose |
|------------|---------|
| **Request Logging** | Log all incoming requests with timing |
| **Rate Limiting** | Prevent abuse via IP-based throttling |
| **CORS** | Allow cross-origin requests from frontend |
| **Error Handling** | Standardize error response format |
| **Request ID** | Attach unique ID to each request for tracing |

### 4.2 New Files Required

| File | Purpose |
|------|---------|
| `app/middleware/logging_middleware.py` | Request/response logging |
| `app/middleware/rate_limit_middleware.py` | IP-based rate limiting |
| `app/middleware/request_id_middleware.py` | Unique request ID injection |
| `app/middleware/error_handler.py` | Global exception handler |

### 4.3 Rate Limiting Strategy

**Algorithm:** Token Bucket via Redis

**Limits:**
| Endpoint Type | Limit |
|---------------|-------|
| Anonymous redirects | 100 req/min per IP |
| Authenticated API | 60 req/min per user |
| Login attempts | 5 req/min per IP |

**Implementation:**
```python
class RateLimitMiddleware:
    async def __call__(self, request, call_next):
        key = f"ratelimit:{request.client.host}"
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        if current > 100:
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        return await call_next(request)
```

### 4.4 Request Logging Format

```json
{
  "request_id": "uuid",
  "method": "GET",
  "path": "/abc123",
  "status_code": 302,
  "duration_ms": 12.5,
  "client_ip": "1.2.3.4",
  "user_id": null,
  "timestamp": "2026-01-21T22:00:00Z"
}
```

### 4.5 Middleware Registration Order

Order matters! Register in `app/main.py`:

```python
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.6 Trade-offs

| Decision | Trade-off |
|----------|-----------|
| **Redis-based rate limiting** | Distributed but adds latency; simpler in-memory won't work with multiple instances |
| **IP-based limiting** | Works for anonymous users, but can block shared IPs (offices, VPNs) |
| **Wildcard CORS** | Easy dev, but not secure for production |
| **Synchronous logging** | Simpler, but adds ~1-2ms per request |

---

## 5. Implementation Order

### Phase 2.1: Database & Models (Day 1)
1. Add `is_active`, `user_id`, `updated_at` to `ShortUrl` model
2. Add relationship between `User` and `ShortUrl`
3. Create Alembic migration
4. Run migration

### Phase 2.2: Authentication (Day 2-3)
1. Create `app/core/security.py` (password hash, JWT)
2. Create `app/repositories/user_repo.py`
3. Create `app/services/auth_service.py`
4. Create `app/api/deps.py` (get_current_user dependency)
5. Create `app/api/v1/routes/auth.py` (register, login, me)
6. Add auth routes to `main.py`
7. Test authentication flow

### Phase 2.3: URL CRUD (Day 4)
1. Add DTOs for update, list, pagination
2. Add repository methods (list, update, delete, soft delete)
3. Add service methods
4. Add route handlers
5. Add ownership checks
6. Test all CRUD operations

### Phase 2.4: Middleware (Day 5)
1. Create request ID middleware
2. Create logging middleware
3. Create rate limiting middleware
4. Create global error handler
5. Configure CORS
6. Register all middleware in order

### Phase 2.5: Events (Day 6)
1. Create event schemas
2. Create publisher
3. Integrate publishing into services
4. Test events are published to Redis

---

## 6. File Structure After Implementation

```
app/
├── api/
│   ├── deps.py                    # NEW: FastAPI dependencies
│   ├── redirect.py
│   └── v1/
│       ├── routes/
│       │   ├── auth.py            # NEW: Auth endpoints
│       │   └── short_urls.py      # MODIFIED: Add CRUD
│       └── schema_dtos.py         # MODIFIED: Add new DTOs
├── core/
│   ├── redis.py
│   ├── security.py                # NEW: JWT & password
│   └── settings.py                # MODIFIED: Add JWT settings
├── events/
│   ├── constants.py               # NEW: Event types
│   ├── publisher.py               # NEW: Redis stream publisher
│   └── schemas.py                 # NEW: Event payloads
├── middleware/
│   ├── error_handler.py           # NEW
│   ├── logging_middleware.py      # NEW
│   ├── rate_limit_middleware.py   # NEW
│   └── request_id_middleware.py   # NEW
├── models/
│   └── url_models.py              # MODIFIED: Add fields
├── repositories/
│   ├── short_url_repo.py          # MODIFIED: Add methods
│   └── user_repo.py               # NEW
├── services/
│   ├── auth_service.py            # NEW
│   └── short_url_service.py       # MODIFIED: Add methods
└── main.py                        # MODIFIED: Register middleware
```

---

## 7. Environment Variables to Add

```env
JWT_SECRET_KEY=your-super-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
BCRYPT_ROUNDS=12
RATE_LIMIT_PER_MINUTE=100
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 8. Summary

This implementation plan provides:

1. **Complete CRUD** for URL management with soft delete
2. **JWT authentication** with refresh token support
3. **Event-driven architecture** via Redis Streams
4. **Production-quality middleware** for logging, rate limiting, and tracing

The trade-offs favor simplicity and demonstration value over enterprise scale, making this ideal for a portfolio project that showcases modern backend architecture patterns.
