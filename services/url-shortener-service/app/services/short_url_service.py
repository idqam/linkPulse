from datetime import datetime
from typing import Optional

from pydantic import HttpUrl

from short_url_repo import ShortUrlRepository
from url_models import ShortUrl
from short_url_service_utils import prepare_url, generate_short_code


class ShortUrlService:
    def __init__(self, repo: ShortUrlRepository):
        self.repo = repo

    def create_short_url(
        self,
        original_url: HttpUrl,
        custom_alias: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        redirect_type: int | None = 302,
    ) -> ShortUrl:

        normalized = prepare_url(original_url)

        short_code = custom_alias or self._generate_unique_code()

        short_url = ShortUrl(
            short_code=short_code,
            original_url=original_url,
            normalized_url=normalized,
            expires_at=expires_at,
            redirect_type=redirect_type,
        )

        return self.repo.create(short_url)

    def _generate_unique_code(self) -> str:
        while True:
            code = generate_short_code()
            if not self.repo.exists(code):
                return code
