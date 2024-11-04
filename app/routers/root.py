from fastapi import APIRouter

from .v1.root import v1_root_router

root_router = APIRouter(prefix="/api")

root_router.include_router(v1_root_router)
