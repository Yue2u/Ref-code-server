import uuid

from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.models import UP
from sqlalchemy import and_, select


class MySQLAlchemyUserDatabase(SQLAlchemyUserDatabase):
    async def get_referrals(self, user_id: uuid.UUID) -> list[UP]:
        stmt = select(self.user_table).where(
            and_(
                self.user_table.referrer_id == user_id,
                self.user_table.is_verified == True,
            )
        )
        return (await self.session.scalars(stmt)).unique().all()
