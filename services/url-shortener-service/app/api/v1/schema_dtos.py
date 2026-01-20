from typing import Optional
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShortURLCreateRequest(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    redirect_type: Optional[int] = 302


class ShortURLCreateResponse(BaseModel):
    short_url: str
    short_code: str
    original_url: HttpUrl | str
    created_at: datetime
    expires_at: Optional[datetime]
    redirect_type: int
    active: bool
    click_count: int
