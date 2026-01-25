from typing import Optional
from redis import asyncio as aioredis
from app.core.settings import settings

class RedisSingleton:
    _instance: Optional[aioredis.Redis] = None

    @classmethod
    def get_instance(cls) -> aioredis.Redis:
        if cls._instance is None:
            cls._instance = aioredis.Redis(
                host=settings.REDIS_URL,
                port=int(settings.REDIS_PORT),
                db=0,
                decode_responses=True,
                socket_timeout=5,  
            )
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

    @classmethod
    async def ping(cls) -> bool:
        try:
            r = cls.get_instance()
            return await r.ping()
        except Exception:
            return False