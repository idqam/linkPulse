from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

from app.api.v1.schema_dtos import (
    ShortURLCreateRequest,
    ShortURLCreateResponse,
    ShortURLUpdateRequest,
    ShortURLListResponse,
    MessageResponse,
)
from app.core.settings import settings
from app.core.redis import RedisSingleton
from app.repositories.short_url_repo import ShortUrlRepository
from app.services.short_url_service import ShortUrlService
from app.models.url_models import ShortUrl, User
from app.db.session import get_db
from app.api.deps import get_current_user, get_current_user_optional


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/short-urls", tags=["short-urls"])


def _build_short_url_response(short_url: ShortUrl) -> ShortURLCreateResponse:
    domain = str(settings.SHORT_URL_DOMAIN or 'http://localhost:8000').rstrip('/')
    return ShortURLCreateResponse(
        short_url=f"{domain}/{short_url.short_code}",
        short_code=short_url.short_code,
        original_url=short_url.original_url,
        created_at=short_url.created_at,
        expires_at=short_url.expires_at,
        redirect_type=short_url.redirect_type,
        active=short_url.is_active and not short_url.is_expired(),
        click_count=short_url.click_count,
        user_id=short_url.user_id,
    )


@router.get("", response_model=ShortURLListResponse)
async def list_short_urls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    result = service.list_user_urls(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        include_inactive=include_inactive,
    )

    return ShortURLListResponse(
        items=[_build_short_url_response(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.get("/{short_code}", response_model=ShortURLCreateResponse)
async def get_short_url(
    short_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    short_url = await service.get_short_url_by_code(short_code)
    if not short_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )

    return _build_short_url_response(short_url)


@router.post("", response_model=ShortURLCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_short_url(
    payload: ShortURLCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    try:
        short_url = service.create_short_url(
            original_url=payload.original_url,
            custom_alias=payload.custom_alias,
            expires_at=payload.expires_at,
            redirect_type=payload.redirect_type,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create short URL",
        )

    return _build_short_url_response(short_url)


@router.patch("/{short_code}", response_model=ShortURLCreateResponse)
async def update_short_url(
    short_code: str,
    payload: ShortURLUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    short_url = repo.get_by_code(short_code)
    if not short_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )

    if not service.verify_ownership(short_url, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this URL"
        )

    updated = service.update_short_url(
        short_url=short_url,
        expires_at=payload.expires_at,
        redirect_type=payload.redirect_type,
    )

    await service.invalidate_cache(short_code)

    return _build_short_url_response(updated)


@router.delete("/{short_code}", response_model=MessageResponse)
async def delete_short_url(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    short_url = repo.get_by_code(short_code)
    if not short_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )

    if not service.verify_ownership(short_url, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this URL"
        )

    await service.invalidate_cache(short_code)
    await service.delete_short_url(short_url)

    return {"message": "Short URL deleted successfully"}


@router.post("/{short_code}/disable", response_model=MessageResponse)
async def disable_short_url(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    short_url = repo.get_by_code(short_code)
    if not short_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )

    if not service.verify_ownership(short_url, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to disable this URL"
        )

    await service.invalidate_cache(short_code)
    await service.disable_short_url(short_url)

    return {"message": "Short URL disabled successfully"}


@router.post("/{short_code}/enable", response_model=MessageResponse)
async def enable_short_url(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo, RedisSingleton)

    short_url = repo.get_by_code(short_code)
    if not short_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )

    if not service.verify_ownership(short_url, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to enable this URL"
        )

    await service.enable_short_url(short_url)

    return {"message": "Short URL enabled successfully"}
