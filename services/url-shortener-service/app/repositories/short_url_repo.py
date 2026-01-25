from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.url_models import ShortUrl


class ShortUrlRepository:
    def __init__(self, db: Session):
        self.db = db

    def exists(self, short_code: str) -> bool:
        return (
            self.db.query(ShortUrl)
            .filter_by(short_code=short_code)
            .first()
            is not None
        )

    def create(self, short_url: ShortUrl) -> ShortUrl:
        self.db.add(short_url)
        self.db.commit()
        self.db.refresh(short_url)
        return short_url

    def get_by_code(self, short_code: str) -> ShortUrl | None:
        return self.db.query(ShortUrl).filter_by(short_code=short_code).first()

    def get_by_code_active(self, short_code: str) -> ShortUrl | None:
        return (
            self.db.query(ShortUrl)
            .filter_by(short_code=short_code, is_active=True)
            .first()
        )

    def increment_clicks(self, short_url: ShortUrl) -> None:
        short_url.click_count += 1
        self.db.commit()
        self.db.refresh(short_url)

    def list_by_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        include_inactive: bool = False,
    ) -> Tuple[List[ShortUrl], int]:
        query = self.db.query(ShortUrl).filter(ShortUrl.user_id == user_id)

        if not include_inactive:
            query = query.filter(ShortUrl.is_active == True)

        total = query.count()

        items = (
            query
            .order_by(desc(ShortUrl.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total

    def update(
        self,
        short_url: ShortUrl,
        expires_at: Optional = None,
        redirect_type: Optional[int] = None,
    ) -> ShortUrl:
        if expires_at is not None:
            short_url.expires_at = expires_at
        if redirect_type is not None:
            short_url.redirect_type = redirect_type

        self.db.commit()
        self.db.refresh(short_url)
        return short_url

    def soft_delete(self, short_url: ShortUrl) -> None:
        short_url.is_active = False
        self.db.commit()

    def restore(self, short_url: ShortUrl) -> None:
        short_url.is_active = True
        self.db.commit()

    def hard_delete(self, short_url: ShortUrl) -> None:
        self.db.delete(short_url)
        self.db.commit()
