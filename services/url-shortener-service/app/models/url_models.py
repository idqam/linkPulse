from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.url_models import ShortUrl


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

    role: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    short_urls: Mapped[List["ShortUrl"]] = relationship(
        "ShortUrl",
        back_populates="owner",
        lazy="dynamic"
    )


class ShortUrl(Base):
    __tablename__ = "short_urls"

    __table_args__ = (
        CheckConstraint(
            "redirect_type IN (301, 302, 303)",
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
        index=True,
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

    click_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="short_urls",
    )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at