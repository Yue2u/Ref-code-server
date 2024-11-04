import uuid
from datetime import timedelta

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    name: str = Field(max_length=128)
    surname: str = Field(max_length=128)
    referrer_id: uuid.UUID | None = None


class UserCreate(schemas.BaseUserCreate):
    name: str = Field(max_length=128)
    surname: str = Field(max_length=128)


class UserUpdate(schemas.BaseUserUpdate):
    name: str = Field(max_length=128)
    surname: str = Field(max_length=128)


class UserReferral(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    name: str
    surname: str


class UserReferrals(BaseModel):
    referrals: list[UserReferral] = []


class ReferralCodeRead(BaseModel):
    referral_code: str


class ReferralCodeReadWithExpire(ReferralCodeRead):
    expires_in: timedelta


class ReferralCodeExpiraton(BaseModel):
    expires_in_seconds: int


class ReferralCodeRequest(BaseModel):
    email: EmailStr
