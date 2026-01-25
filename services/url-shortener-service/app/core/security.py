from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.core.settings import settings
from app.core.redis import RedisSingleton


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password, rounds=settings.BCRYPT_ROUNDS)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "jti": jti,
        "exp": expire,
        "type": "refresh"
    }
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def store_refresh_token(user_id: int, jti: str) -> None:
    redis = RedisSingleton.get_instance()
    key = f"refresh_token:{user_id}:{jti}"
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis.setex(key, ttl, "valid")


async def revoke_refresh_token(user_id: int, jti: str) -> None:
    redis = RedisSingleton.get_instance()
    key = f"refresh_token:{user_id}:{jti}"
    await redis.delete(key)


async def is_refresh_token_valid(user_id: int, jti: str) -> bool:
    redis = RedisSingleton.get_instance()
    key = f"refresh_token:{user_id}:{jti}"
    result = await redis.get(key)
    return result == "valid"


async def revoke_all_user_tokens(user_id: int) -> None:
    redis = RedisSingleton.get_instance()
    pattern = f"refresh_token:{user_id}:*"
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break
