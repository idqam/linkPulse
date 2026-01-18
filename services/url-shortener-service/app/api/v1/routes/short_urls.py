from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.api.v1.schema_dtos import ShortURLCreateRequest, ShortURLCreateResponse
from app.core.settings import settings
from app.repositories.short_url_repo import ShortUrlRepository
from app.services.short_url_service import ShortUrlService
from app.models.url_models import ShortUrl
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/short-urls", tags=["short-urls"])

@router.get(
        "",
        response_model=ShortURLCreateResponse,
        status_code=status.HTTP_200_OK,
)

def get_short_url(payload: str, db: Session = Depends(get_db)):
    pass

@router.post(
    "",
    response_model=ShortURLCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_short_url(
    payload: ShortURLCreateRequest,
    db: Session = Depends(get_db),
):
    repo = ShortUrlRepository(db)
    service = ShortUrlService(repo)

    try:
        short_url: ShortUrl = service.create_short_url(
            original_url=payload.original_url,
            custom_alias=payload.custom_alias,
            expires_at=payload.expires_at,
            redirect_type=payload.redirect_type,
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create short URL: {str(e)}",
        )

    return ShortURLCreateResponse(
        short_url=f"{str(settings.SHORT_URL_DOMAIN or 'http://localhost:8000').rstrip('/')}/{short_url.short_code}",
        short_code=short_url.short_code,
        original_url=short_url.original_url,
        created_at=short_url.created_at,
        expires_at=short_url.expires_at,
        redirect_type=short_url.redirect_type,
        active=True,
    )
