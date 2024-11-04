import asyncio
import secrets
import uuid
from typing import Annotated

from fastapi import Depends

from app.core.auth.settings import settings
from app.db.redis import Redis, get_redis


class ReferralCodeManager:
    def __init__(
        self,
        redis: Redis,
        uid_to_code_prefix=settings.REDIS_UID_TO_REF_CODE_RPEFIX,
        code_to_uid_prefix=settings.REDIS_REF_CODE_TO_UID_RPEFIX,
    ):
        self.redis: Redis = redis
        self.uid_to_code_prefix = uid_to_code_prefix
        self.code_to_uid_prefix = code_to_uid_prefix

    async def retrieve_code(self, user_id: uuid.UUID) -> str | None:
        return await self.redis.get(f"{self.uid_to_code_prefix}{user_id}")

    async def retieve_user_id_by_code(self, ref_code: str) -> uuid.UUID | None:
        uid = await self.redis.get(f"{self.code_to_uid_prefix}{ref_code}")
        print(uid)
        return uuid.UUID(uid)

    async def retrieve_ttl_by_user_id(self, user_id: uuid.UUID):
        return await self.redis.ttl(f"{self.uid_to_code_prefix}{user_id}")

    async def retrieve_ttl_by_ref_code(self, ref_code: str):
        return await self.redis.ttl(f"{self.code_to_uid_prefix}{ref_code}")

    async def create(self, user_id: uuid.UUID, ttl: int) -> str | None:
        stored_ttl = await self.retrieve_ttl_by_user_id(user_id)
        if stored_ttl >= 0:
            return None

        new_ref_code = secrets.token_urlsafe(8)

        await asyncio.gather(
            self.redis.set(
                f"{self.uid_to_code_prefix}{user_id}",
                new_ref_code,
                ex=ttl,
            ),
            self.redis.set(
                f"{self.code_to_uid_prefix}{new_ref_code}",
                str(user_id),
                ex=ttl,
            ),
        )
        return new_ref_code

    async def delete(self, user_id: uuid.UUID) -> bool:
        stored_ttl = await self.retrieve_ttl_by_user_id(user_id)
        if stored_ttl < 0:
            return False

        ref_code = await self.retrieve_code(user_id)

        await asyncio.gather(
            self.redis.delete(f"{self.uid_to_code_prefix}{user_id}"),
            self.redis.delete(f"{self.retrieve_ttl_by_ref_code}{ref_code}"),
        )
        return True


async def get_ref_code_manager(
    redis: Annotated[Redis, Depends(get_redis)]
) -> ReferralCodeManager:
    return ReferralCodeManager(redis)
