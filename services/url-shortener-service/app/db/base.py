# app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass



from app.models.url_models import ShortUrl, User  # noqa: E402,F401
