from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from schema_dtos import ShortURLCreateRequest, ShortURLCreateResponse
import settings
from short_url_repo import ShortUrlRepository
from short_url_service import ShortUrlService
from url_models import ShortUrl
from settings import Settings
from db.session import get_db
router = APIRouter(prefix="/short-urls", tags=["short-urls"])


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create short URL",
        )

    return ShortURLCreateResponse(
        short_url=f"{str(Settings.SHORT_URL_DOMAIN).rstrip('/')}/{short_url.short_code}",
        short_code=short_url.short_code,
        original_url=short_url.original_url,
        created_at=short_url.created_at,
        expires_at=short_url.expires_at,
        redirect_type=short_url.redirect_type,
        active=True,
    )
