from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass
