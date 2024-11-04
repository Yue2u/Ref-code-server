from redis.asyncio import Redis

from .settings import settings


def get_redis() -> Redis:
    raise NotImplementedError()


def create_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)
