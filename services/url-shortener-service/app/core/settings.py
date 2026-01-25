from typing import Optional, List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SHORT_URL_DOMAIN: Optional[AnyHttpUrl] = None
    DATABASE_URL: str
    REDIS_URL: str
    REDIS_PORT: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    RATE_LIMIT_PER_MINUTE: int = 100
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
