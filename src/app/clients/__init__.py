"""Clients for external resources: the application's data access layer."""

from app.clients.redis.create_redis_key import create_redis_key
from app.clients.redis.redis_client import RedisClient

__all__ = [
    "RedisClient",
    "create_redis_key",
]
