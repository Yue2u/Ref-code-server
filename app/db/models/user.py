import uuid

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from .base import Base
from .oauth_account import OAuthAccount


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User sqlalchemy model."""

    name: Mapped[str] = mapped_column(String(length=128))
    surname: Mapped[str] = mapped_column(String(length=128))

    referrer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True, default=None
    )

    referrals: Mapped[list["User"]] = relationship(
        backref=backref("referrer", remote_side="User.id")
    )
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(lazy="joined")