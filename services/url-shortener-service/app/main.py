from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.short_urls import router as short_urls_router
from app.api.v1.routes.auth import router as auth_router
from app.api.redirect import router as redirect_router
from app.core.redis import RedisSingleton
from app.core.settings import settings
from app.middleware.request_id_middleware import RequestIDMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LinkPulse URL Shortener Service")
    await RedisSingleton.ping()
    logger.info("Redis connection established")
    yield
    await RedisSingleton.close()
    logger.info("Redis connection closed")


app = FastAPI(
    title="LinkPulse URL Shortener",
    description="A high-performance URL shortening service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(short_urls_router, prefix="/api/v1")
app.include_router(redirect_router)


@app.get("/health")
async def health():
    redis_ok = await RedisSingleton.ping()
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
    }
