from typing import Optional
from sqlalchemy.orm import Session

from app.models.url_models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def exists_by_email(self, email: str) -> bool:
        return self.db.query(User).filter(User.email == email).first() is not None

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_last_login(self, user: User) -> None:
        from datetime import datetime, timezone
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)

    def deactivate(self, user: User) -> None:
        user.is_active = False
        self.db.commit()

    def activate(self, user: User) -> None:
        user.is_active = True
        self.db.commit()
