from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base  

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )




class ShortUrl(Base):
    __tablename__ = "short_urls"

    __table_args__ = (
        CheckConstraint(
            "redirect_type IN (301, 302)",
            name="ck_short_urls_redirect_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    short_code: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        unique=True,
    )

    original_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    normalized_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    redirect_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=302,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at