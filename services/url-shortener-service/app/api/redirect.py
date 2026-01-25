from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.repositories.short_url_repo import ShortUrlRepository
from app.services.short_url_service import ShortUrlService
from app.core.redis import RedisSingleton
from app.events.publisher import event_publisher
from app.events.constants import EVENT_URL_ACCESSED
from app.events.schemas import UrlAccessedEvent


logger = logging.getLogger(__name__)
router = APIRouter(tags=["redirect"])


@router.get("/{short_code}", response_class=RedirectResponse)
async def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    try:
        short_url = await service.get_short_url_by_code(short_code)

        if not short_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short URL not found"
            )

        if short_url.is_expired():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Short URL has expired"
            )

        service.record_visit(short_url)

        event = UrlAccessedEvent(
            short_code=short_code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            timestamp=datetime.now(timezone.utc),
        )
        await event_publisher.publish(EVENT_URL_ACCESSED, event)

        return RedirectResponse(
            url=short_url.original_url,
            status_code=short_url.redirect_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redirect error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
