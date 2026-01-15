from typing import Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SHORT_URL_DOMAIN: Optional[AnyHttpUrl] = None
    DATA_BASE_URL: str = ''

    class Config:
        env_file = ".env"

settings = Settings()
