from fastapi import APIRouter

from .user import router as user_router


v1_root_router = APIRouter(prefix="/v1")

v1_root_router.include_router(user_router)