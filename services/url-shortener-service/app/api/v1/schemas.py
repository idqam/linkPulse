from typing import Optional
from pydantic import BaseModel


class ShortURLCreateRequest(BaseModel):
    original_url: str
    custom_alias: Optional[str]
    expires_at: Optional[float]
    redirect_type: Optional[str]
    meta_data: Optional[str]

class ShortURLResponseRequest(BaseModel):
    short_url: str
    short_code: str 
    original_url: str
    created_at: float
    expires_at: Optional[float]
    redirect_type: str
    status: str
