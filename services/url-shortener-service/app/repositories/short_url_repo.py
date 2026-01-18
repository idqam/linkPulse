from sqlalchemy.orm import Session

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
