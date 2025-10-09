"""
Redis Cache Client for DarkHorses Workers
Handles cache invalidation when database is updated
"""

import os
import logging

logger = logging.getLogger('LIVE_ODDS')

# Try to import upstash-redis
try:
    from upstash_redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("upstash-redis not installed - cache invalidation disabled")
    REDIS_AVAILABLE = False
    Redis = None


class RedisCache:
    """Redis cache client for workers - invalidation only"""

    def __init__(self):
        """Initialize Redis connection from environment variables"""
        self.client = None
        self.enabled = False

        if not REDIS_AVAILABLE:
            logger.debug("Redis cache invalidation disabled - upstash-redis not available")
            return

        # Get Upstash credentials from environment
        redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')

        if not redis_url or not redis_token:
            logger.debug("Redis credentials not found in environment - cache invalidation disabled")
            return

        try:
            # Initialize Upstash Redis client
            self.client = Redis(url=redis_url, token=redis_token)

            # Test connection with ping
            self.client.ping()

            self.enabled = True
            logger.info(f"✅ Redis cache invalidation connected: {redis_url}")

        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed (cache invalidation disabled): {e}")
            self.client = None
            self.enabled = False

    def invalidate_races_cache(self) -> bool:
        """
        Invalidate the races-by-stage cache
        Called after workers update the database
        """
        if not self.enabled or not self.client:
            return False

        try:
            # Delete the main cache key
            self.client.delete("races:by-stage:v1")
            logger.info("🗑️  Invalidated races cache - next API request will fetch fresh data")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Failed to invalidate cache: {e}")
            return False


# Global singleton instance
_redis_cache = None

def get_redis_cache() -> RedisCache:
    """Get or create Redis cache singleton"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def invalidate_races_cache():
    """Convenience function to invalidate races cache"""
    return get_redis_cache().invalidate_races_cache()
