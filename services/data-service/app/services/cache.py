"""
Redis caching service for data service
"""
import logging
from typing import Optional
from redis import Redis, RedisError
from app.config import config

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service"""
    
    def __init__(self, redis_url: Optional[str] = None, ttl: Optional[int] = None):
        """
        Initialize cache service
        
        Args:
            redis_url: Redis connection URL (defaults to config value)
            ttl: Time-to-live in seconds (defaults to config value)
        """
        self.redis_url = redis_url or config.REDIS_URL
        self.ttl = ttl or config.CACHE_TTL
        self.client: Optional[Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except (RedisError, Exception) as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
            else:
                logger.debug(f"Cache miss for key: {key}")
            return value
        except RedisError as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (defaults to service TTL)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            cache_ttl = ttl or self.ttl
            self.client.setex(key, cache_ttl, value)
            logger.debug(f"Cached key: {key} with TTL: {cache_ttl}s")
            return True
        except RedisError as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return True
        except RedisError as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except RedisError:
            return False
    
    def close(self):
        """Close Redis connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except RedisError as e:
                logger.error(f"Error closing Redis connection: {e}")
