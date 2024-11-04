from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .db.redis import create_redis_client, get_redis
from .routers.root import root_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = create_redis_client()
    app.dependency_overrides[get_redis] = lambda: redis_client

    yield

    await redis_client.aclose()


fastapi_app = FastAPI(
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
    ],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Access-Control-Allow-Headers",
        "Content-Type",
        "Authorization",
        "Access-Control-Allow-Origin",
        "Set-Cookie",
    ],
    allow_credentials=True,
)

fastapi_app.include_router(root_router)
