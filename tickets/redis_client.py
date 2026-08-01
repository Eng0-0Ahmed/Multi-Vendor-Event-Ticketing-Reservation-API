import redis
from django.conf import settings

pool = redis.ConnectionPool(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=0,
    decode_responses=True
)

def get_redis_client():
    return redis.Redis(connection_pool=pool)