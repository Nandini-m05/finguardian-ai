import redis.asyncio as redis
from app.config import settings

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return a shared Redis client, creating it on first use.

    redis-py manages its own connection pool internally, so we reuse
    one client instance rather than opening a fresh connection every
    time something needs to publish - opening one per call would be
    slow and wasteful.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def publish_event(stream: str, event: dict) -> str:
    """Publish a flat field-value event onto a Redis Stream."""
    client = get_redis_client()
    entry_id = await client.xadd(stream, event)
    return entry_id
