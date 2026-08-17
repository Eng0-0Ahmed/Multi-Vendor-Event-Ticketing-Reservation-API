import redis
from django.conf import settings

redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')

pool = redis.ConnectionPool.from_url(
    redis_url,
    decode_responses=True
)

def get_redis_client():
    return redis.Redis(connection_pool=pool)