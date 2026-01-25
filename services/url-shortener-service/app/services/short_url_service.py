from datetime import datetime
from typing import Optional, Tuple, List
import math
import asyncio

from pydantic import HttpUrl

from app.core.redis import RedisSingleton
from app.repositories.short_url_repo import ShortUrlRepository
from app.models.url_models import ShortUrl, User
from app.utils.short_url_service_utils import prepare_url, generate_short_code
from app.api.v1.schema_dtos import ShortURLCacheModel
from app.events.publisher import event_publisher
from app.events.schemas import (
    UrlCreatedEvent,
    UrlUpdatedEvent,
    UrlDeletedEvent,
    UrlStatusChangedEvent,
)
from app.events.constants import (
    EVENT_URL_CREATED,
    EVENT_URL_UPDATED,
    EVENT_URL_DELETED,
    EVENT_URL_DISABLED,
    EVENT_URL_ENABLED,
)


class ShortUrlService:
    def __init__(self, repo: ShortUrlRepository, redis: RedisSingleton):
        self.repo = repo
        self.redis = redis

    def create_short_url(
        self,
        original_url: HttpUrl,
        custom_alias: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        redirect_type: int | None = 302,
        user_id: Optional[int] = None,
    ) -> ShortUrl:
        normalized = prepare_url(original_url)
        short_code = custom_alias or self._generate_unique_code()

        if custom_alias and self.repo.exists(custom_alias):
            raise ValueError("Custom alias already exists")

        short_url = ShortUrl(
            short_code=short_code,
            original_url=str(original_url),
            normalized_url=normalized,
            expires_at=expires_at,
            redirect_type=redirect_type,
            user_id=user_id,
        )

        short_url = self.repo.create(short_url)

        event = UrlCreatedEvent(
            short_code=short_url.short_code,
            original_url=short_url.original_url,
            user_id=short_url.user_id,
            timestamp=datetime.now(timezone.utc),
        )
       
        asyncio.create_task(event_publisher.publish(EVENT_URL_CREATED, event))

        return short_url

    def _generate_unique_code(self) -> str:
        while True:
            code = generate_short_code()
            if not self.repo.exists(code):
                return code

    async def get_short_url_by_code(self, short_code: str) -> Optional[ShortUrl]:
        r = self.redis.get_instance()

        cached_data = await r.get(short_code)
        if cached_data:
            try:
                data = ShortURLCacheModel.model_validate_json(cached_data)
                return ShortUrl(
                    short_code=data.short_code,
                    original_url=data.original_url,
                    redirect_type=data.redirect_type,
                    expires_at=data.expires_at,
                )
            except Exception:
                pass

        short_url = self.repo.get_by_code_active(short_code)

        if short_url:
            cache_model = ShortURLCacheModel(
                short_code=short_url.short_code,
                original_url=short_url.original_url,
                redirect_type=short_url.redirect_type,
                expires_at=short_url.expires_at
            )
            await r.setex(short_code, 3600, cache_model.model_dump_json())

        return short_url

    def record_visit(self, short_url: ShortUrl) -> None:
        self.repo.increment_clicks(short_url)

    def list_user_urls(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        include_inactive: bool = False,
    ) -> dict:
        items, total = self.repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            include_inactive=include_inactive,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def update_short_url(
        self,
        short_url: ShortUrl,
        expires_at: Optional[datetime] = None,
        redirect_type: Optional[int] = None,
    ) -> ShortUrl:
        updated = self.repo.update(
            short_url=short_url,
            expires_at=expires_at,
            redirect_type=redirect_type,
        )

        
        changes = {}
        if expires_at is not None:
            changes["expires_at"] = expires_at.isoformat()
        if redirect_type is not None:
            changes["redirect_type"] = redirect_type

        if changes and updated.user_id:
            event = UrlUpdatedEvent(
                short_code=updated.short_code,
                user_id=updated.user_id,
                changes=changes,
                timestamp=datetime.now(timezone.utc),
            )
            import asyncio
            asyncio.create_task(event_publisher.publish(EVENT_URL_UPDATED, event))

        return updated

    async def invalidate_cache(self, short_code: str) -> None:
        r = self.redis.get_instance()
        await r.delete(short_code)

    async def disable_short_url(self, short_url: ShortUrl) -> None:
        self.repo.soft_delete(short_url)
        if short_url.user_id:
            event = UrlStatusChangedEvent(
                short_code=short_url.short_code,
                user_id=short_url.user_id,
                new_status="disabled",
                timestamp=datetime.now(timezone.utc),
            )
            await event_publisher.publish(EVENT_URL_DISABLED, event)

    async def enable_short_url(self, short_url: ShortUrl) -> None:
        self.repo.restore(short_url)
        if short_url.user_id:
            event = UrlStatusChangedEvent(
                short_code=short_url.short_code,
                user_id=short_url.user_id,
                new_status="active",
                timestamp=datetime.now(timezone.utc),
            )
            await event_publisher.publish(EVENT_URL_ENABLED, event)

    async def delete_short_url(self, short_url: ShortUrl) -> None:
        short_code = short_url.short_code
        user_id = short_url.user_id
        self.repo.hard_delete(short_url)
        if user_id:
            event = UrlDeletedEvent(
                short_code=short_code,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
            )
            await event_publisher.publish(EVENT_URL_DELETED, event)

    def verify_ownership(self, short_url: ShortUrl, user: User) -> bool:
        if user.role == "admin":
            return True
        return short_url.user_id == user.id