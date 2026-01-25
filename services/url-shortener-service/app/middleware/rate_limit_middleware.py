from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.redis import RedisSingleton
from app.core.settings import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"

        redis = RedisSingleton.get_instance()
        current = await redis.incr(key)

        if current == 1:
            await redis.expire(key, 60)

        if current > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(max(0, settings.RATE_LIMIT_PER_MINUTE - current))

        return response
