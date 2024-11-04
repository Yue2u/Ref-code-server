import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db import get_session
from app.db.models.oauth_account import OAuthAccount
from app.db.models.user import User
from app.db.redis import create_redis_client
from app.ref_code_manager import ReferralCodeManager

from .settings import settings as auth_settings
from .user_db import MySQLAlchemyUserDatabase


async def get_user_db(session: Annotated[AsyncSession, Depends(get_session)]):
    yield MySQLAlchemyUserDatabase(session, User, OAuthAccount)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = auth_settings.RESTORE_PASSWORD_SECRET
    verification_token_secret = auth_settings.VERIFICATION_SECRET

    async def get_referrals(self, user_id: uuid.UUID) -> list[User]:
        return await self.user_db.get_referrals(user_id)

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        print(f"User {user.id} requested verification. Token: {token}.")

    async def on_before_delete(
        self, user: User, request: Request | None = None
    ) -> None:
        new_redis = create_redis_client()
        await ReferralCodeManager(new_redis).delete(user.id)
        await new_redis.aclose()


async def get_user_manager(
    user_db: Annotated[MySQLAlchemyUserDatabase, Depends(get_user_db)]
):
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        auth_settings.ACCESS_SECRET, lifetime_seconds=auth_settings.ACCESS_LIFETIME
    )


def get_jwt_refresh_strategy() -> JWTStrategy:
    return JWTStrategy(
        auth_settings.REFRESH_SECRET, lifetime_seconds=auth_settings.REFRESH_LIFETIME
    )


bearer_transport = BearerTransport(tokenUrl="/api/v1/auth/login")

auth_backend = AuthenticationBackend(
    "jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

fastapi_users_app = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_verified_user = fastapi_users_app.current_user(active=True, verified=True)
