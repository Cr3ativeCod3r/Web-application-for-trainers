from functools import cache

import redis
from django.conf import settings


@cache
def get_bus() -> redis.Redis:
    """Redis connection used as the message bus (Redis Streams)."""
    return redis.Redis.from_url(settings.EVENT_BUS_URL, decode_responses=True)
