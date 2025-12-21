"""
CIAL Redis Manager
Connection and management for Redis-based Short-Term Memory
"""

import json
from datetime import timedelta
from typing import Any, Dict, Optional

import redis
from redis.asyncio import Redis as AsyncRedis

from infrastructure.config import settings
from infrastructure.logging_config import logger


class RedisManager:
    """
    Redis connection manager for CIAL Short-Term Memory.

    Provides sync and async Redis connections with connection pooling.
    """

    def __init__(self):
        self._sync_client: redis.Redis | None = None
        self._async_client: AsyncRedis | None = None
        self._connected = False

    def connect(self):
        """Initialize Redis connections (synchronous)."""
        try:
            # Create connection pool
            pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )

            self._sync_client = redis.Redis(connection_pool=pool)

            # Test connection
            self._sync_client.ping()
            self._connected = True

            logger.info(
                "Redis connected successfully",
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
            )

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    async def connect_async(self):
        """Initialize async Redis connection."""
        try:
            self._async_client = await AsyncRedis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
            )

            # Test connection
            await self._async_client.ping()

            logger.info("Async Redis connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to async Redis: {e}", exc_info=True)
            raise

    def disconnect(self):
        """Close Redis connections."""
        if self._sync_client:
            self._sync_client.close()
            self._connected = False
            logger.info("Redis disconnected")

    async def disconnect_async(self):
        """Close async Redis connection."""
        if self._async_client:
            await self._async_client.close()
            logger.info("Async Redis disconnected")

    @property
    def client(self) -> redis.Redis:
        """Get synchronous Redis client."""
        if not self._sync_client or not self._connected:
            self.connect()
        return self._sync_client

    @property
    def async_client(self) -> AsyncRedis:
        """Get asynchronous Redis client."""
        if not self._async_client:
            raise RuntimeError("Async Redis client not initialized. Call connect_async() first.")
        return self._async_client

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        try:
            if self._sync_client:
                self._sync_client.ping()
                return True
        except:
            pass
        return False

    def get_info(self) -> dict[str, Any]:
        """Get Redis server information."""
        if not self.is_connected():
            return {"connected": False}

        info = self.client.info()
        return {
            "connected": True,
            "version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace": self.client.dbsize(),
        }


# Global Redis manager instance
_redis_manager: RedisManager | None = None


def get_redis_manager() -> RedisManager:
    """
    Get the global Redis manager instance.
    Uses singleton pattern.

    Returns:
        RedisManager: Global Redis manager
    """
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager
