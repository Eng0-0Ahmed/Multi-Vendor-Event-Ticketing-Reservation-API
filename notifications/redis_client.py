import os
import redis
from django.conf import settings


def get_redis_url():
    return os.getenv("REDIS_URL") or getattr(settings, "REDIS_URL", "redis://redis:6379/0")


def get_redis_client():
    return redis.Redis.from_url(get_redis_url(), decode_responses=True)