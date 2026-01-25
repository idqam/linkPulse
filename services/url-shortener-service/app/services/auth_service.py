from datetime import datetime, timezone
from typing import Optional

from app.models.url_models import User
from app.repositories.user_repo import UserRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    revoke_refresh_token,
    is_refresh_token_valid,
    decode_token,
    revoke_all_user_tokens,
)
from app.events.publisher import event_publisher
from app.events.schemas import UserRegisteredEvent, UserLoggedInEvent
from app.events.constants import EVENT_USER_REGISTERED, EVENT_USER_LOGGED_IN


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, email: str, password: str) -> User:
        if self.user_repo.exists_by_email(email):
            raise ValueError("Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(password),
        )
        user = self.user_repo.create(user)

        event = UserRegisteredEvent(
            user_id=user.id,
            email=user.email,
            timestamp=datetime.now(timezone.utc),
        )
        import asyncio
        asyncio.create_task(event_publisher.publish(EVENT_USER_REGISTERED, event))

        return user

    async def login(self, email: str, password: str, ip_address: Optional[str] = None) -> Optional[dict]:
        user = self.user_repo.get_by_email(email)
        if not user:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        self.user_repo.update_last_login(user)

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        refresh_token, jti = create_refresh_token(user.id)
        await store_refresh_token(user.id, jti)

        event = UserLoggedInEvent(
            user_id=user.id,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
        )
        import asyncio
        asyncio.create_task(event_publisher.publish(EVENT_USER_LOGGED_IN, event))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
        }

    async def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        payload = decode_token(refresh_token)
        if not payload:
            return None

        if payload.get("type") != "refresh":
            return None

        user_id = int(payload.get("sub"))
        jti = payload.get("jti")

        if not await is_refresh_token_valid(user_id, jti):
            return None

        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    async def logout(self, refresh_token: str) -> bool:
        payload = decode_token(refresh_token)
        if not payload:
            return False

        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        await revoke_refresh_token(user_id, jti)
        return True

    async def logout_all(self, user_id: int) -> None:
        await revoke_all_user_tokens(user_id)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.user_repo.get_by_id(user_id)
