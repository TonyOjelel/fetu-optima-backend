import redis.asyncio as redis
from app.core.config import settings

# Create Redis pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=10,
    decode_responses=True
)

async def get_redis():
    """Get Redis connection from pool"""
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.close()

class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set(self, key: str, value: str, expire: int = 3600):
        """Set key with expiration"""
        await self.redis.set(key, value, ex=expire)

    async def get(self, key: str) -> str:
        """Get value by key"""
        return await self.redis.get(key)

    async def delete(self, key: str):
        """Delete key"""
        await self.redis.delete(key)

    async def increment(self, key: str) -> int:
        """Increment value"""
        return await self.redis.incr(key)

    async def add_to_sorted_set(self, key: str, score: float, member: str):
        """Add to sorted set"""
        await self.redis.zadd(key, {member: score})

    async def get_sorted_set_range(self, key: str, start: int, end: int, desc: bool = True):
        """Get range from sorted set"""
        return await self.redis.zrange(key, start, end, desc=desc, withscores=True)
