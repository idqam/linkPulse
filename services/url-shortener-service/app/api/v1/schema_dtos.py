from typing import Optional
from datetime import datetime

from pydantic import BaseModel, HttpUrl, EmailStr, Field


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
    user_id: Optional[int] = None


class ShortURLUpdateRequest(BaseModel):
    expires_at: Optional[datetime] = None
    redirect_type: Optional[int] = None


class ShortURLListResponse(BaseModel):
    items: list[ShortURLCreateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ShortURLCacheModel(BaseModel):
    short_code: str
    original_url: str
    redirect_type: int
    expires_at: Optional[datetime]


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    email: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    role: str
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
