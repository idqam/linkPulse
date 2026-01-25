from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class UrlCreatedEvent(BaseModel):
    short_code: str
    original_url: str
    user_id: Optional[int]
    timestamp: datetime


class UrlAccessedEvent(BaseModel):
    short_code: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    referrer: Optional[str]
    timestamp: datetime


class UrlUpdatedEvent(BaseModel):
    short_code: str
    user_id: int
    changes: dict
    timestamp: datetime


class UrlDeletedEvent(BaseModel):
    short_code: str
    user_id: int
    timestamp: datetime


class UrlStatusChangedEvent(BaseModel):
    short_code: str
    user_id: int
    new_status: str
    timestamp: datetime


class UserRegisteredEvent(BaseModel):
    user_id: int
    email: str
    timestamp: datetime


class UserLoggedInEvent(BaseModel):
    user_id: int
    ip_address: Optional[str]
    timestamp: datetime


class UserLoggedOutEvent(BaseModel):
    user_id: int
    timestamp: datetime
