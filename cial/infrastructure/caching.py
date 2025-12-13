"""
CIAL Caching Layer Enhancement
Session 17: Advanced caching with aiocache, cache-aside pattern, warming, and invalidation

Features:
- Multi-tier caching (Redis + in-memory)
- Cache-aside pattern implementation
- Intelligent cache warming for popular symbols
- Smart cache invalidation strategies
- Cache statistics and monitoring
- Decorator-based caching for easy integration
"""

from typing import Optional, Any, Dict, List, Callable, Union
from functools import wraps
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from aiocache import Cache, caches
from aiocache.serializers import JsonSerializer
from aiocache.plugins import BasePlugin
import time

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.observability import metrics, trace_operation


# Configure aiocache backends
caches.set_config({
    'default': {
        'cache': "aiocache.RedisCache",
        'endpoint': settings.REDIS_HOST,
        'port': settings.REDIS_PORT,
        'db': settings.REDIS_DB,
        'password': settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        'serializer': {
            'class': "aiocache.serializers.JsonSerializer"
        },
        'plugins': []
    },
    'memory': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.JsonSerializer"
        }
    }
})


class CacheMetricsPlugin(BasePlugin):
    """
    Plugin to track cache hit/miss metrics for Prometheus.
    Integrates with Session 14 Observability infrastructure.
    """

    async def pre_get(self, *args, **kwargs):
        """Called before cache get operation."""
        pass

    async def post_get(self, took_time, key, ret):
        """Called after cache get operation."""
        cache_type = "redis"
        if ret is not None:
            # Cache hit
            metrics.increment_counter(
                'cial_cache_hits_total',
                {'cache_type': cache_type, 'operation': 'get'}
            )
        else:
            # Cache miss
            metrics.increment_counter(
                'cial_cache_misses_total',
                {'cache_type': cache_type, 'operation': 'get'}
            )

        # Record operation duration
        metrics.record_histogram(
            'cial_cache_operation_seconds',
            took_time,
            {'cache_type': cache_type, 'operation': 'get'}
        )


class CacheManager:
    """
    Centralized cache management with multi-tier caching strategy.

    Implements:
    - L1 Cache: In-memory (fastest, limited capacity)
    - L2 Cache: Redis (shared across instances, larger capacity)
    - Cache-aside pattern
    - Cache warming
    - Intelligent invalidation
    """

    def __init__(self):
        self.redis_cache = Cache(Cache.REDIS, **{
            'endpoint': settings.REDIS_HOST,
            'port': settings.REDIS_PORT,
            'db': settings.REDIS_DB,
            'password': settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            'serializer': JsonSerializer(),
        })

        self.memory_cache = Cache(Cache.MEMORY, serializer=JsonSerializer())

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'warmings': 0
        }

        # Popular symbols for cache warming
        self.popular_symbols = [
            'bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot',
            'avalanche', 'polygon', 'chainlink', 'uniswap', 'aave'
        ]

        # Cache warming interval (seconds)
        self.warming_interval = 300  # 5 minutes

        # Background warming task
        self._warming_task: Optional[asyncio.Task] = None

    @trace_operation("cache_get")
    async def get(
        self,
        key: str,
        cache_tier: str = "both"
    ) -> Optional[Any]:
        """
        Get value from cache with multi-tier support.

        Args:
            key: Cache key
            cache_tier: "memory", "redis", or "both" (default)

        Returns:
            Cached value or None if not found
        """
        start_time = time.time()

        try:
            # Try L1 cache (memory) first if enabled
            if cache_tier in ["both", "memory"]:
                value = await self.memory_cache.get(key)
                if value is not None:
                    self.stats['hits'] += 1
                    metrics.increment_counter(
                        'cial_cache_hits_total',
                        {'tier': 'memory', 'operation': 'get'}
                    )
                    logger.debug(f"Cache hit (memory): {key}")
                    return value

            # Try L2 cache (Redis)
            if cache_tier in ["both", "redis"]:
                value = await self.redis_cache.get(key)
                if value is not None:
                    self.stats['hits'] += 1
                    metrics.increment_counter(
                        'cial_cache_hits_total',
                        {'tier': 'redis', 'operation': 'get'}
                    )

                    # Promote to L1 cache for faster access
                    if cache_tier == "both":
                        await self.memory_cache.set(key, value, ttl=60)

                    logger.debug(f"Cache hit (redis): {key}")
                    return value

            # Cache miss
            self.stats['misses'] += 1
            metrics.increment_counter(
                'cial_cache_misses_total',
                {'tier': cache_tier, 'operation': 'get'}
            )
            logger.debug(f"Cache miss: {key}")
            return None

        finally:
            duration = time.time() - start_time
            metrics.record_histogram(
                'cial_cache_operation_seconds',
                duration,
                {'operation': 'get', 'tier': cache_tier}
            )

    @trace_operation("cache_set")
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_tier: str = "both"
    ) -> bool:
        """
        Set value in cache with multi-tier support.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = no expiry)
            cache_tier: "memory", "redis", or "both" (default)

        Returns:
            True if successful
        """
        start_time = time.time()

        try:
            # Set in L1 cache (memory)
            if cache_tier in ["both", "memory"]:
                # Memory cache: shorter TTL (max 1 hour) to prevent memory bloat
                memory_ttl = min(ttl or 3600, 3600)
                await self.memory_cache.set(key, value, ttl=memory_ttl)

            # Set in L2 cache (Redis)
            if cache_tier in ["both", "redis"]:
                await self.redis_cache.set(key, value, ttl=ttl)

            self.stats['sets'] += 1
            metrics.increment_counter(
                'cial_cache_sets_total',
                {'tier': cache_tier}
            )

            logger.debug(f"Cache set: {key} (ttl={ttl}s, tier={cache_tier})")
            return True

        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

        finally:
            duration = time.time() - start_time
            metrics.record_histogram(
                'cial_cache_operation_seconds',
                duration,
                {'operation': 'set', 'tier': cache_tier}
            )

    @trace_operation("cache_delete")
    async def delete(self, key: str, cache_tier: str = "both") -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete
            cache_tier: "memory", "redis", or "both" (default)

        Returns:
            True if successful
        """
        try:
            if cache_tier in ["both", "memory"]:
                await self.memory_cache.delete(key)

            if cache_tier in ["both", "redis"]:
                await self.redis_cache.delete(key)

            self.stats['deletes'] += 1
            metrics.increment_counter(
                'cial_cache_deletes_total',
                {'tier': cache_tier}
            )

            logger.debug(f"Cache deleted: {key} (tier={cache_tier})")
            return True

        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    @trace_operation("cache_invalidate_pattern")
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "price:*", "intelligence:bitcoin:*")

        Returns:
            Number of keys deleted
        """
        try:
            # Get Redis client from cache
            from infrastructure.container import get_container
            container = get_container()
            redis_manager = container.redis_manager()
            client = redis_manager.async_client

            # Find all matching keys
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            # Delete keys
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Invalidated {deleted} keys matching pattern: {pattern}")

                metrics.increment_counter(
                    'cial_cache_invalidations_total',
                    {'pattern': pattern},
                    deleted
                )

                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache invalidation failed for pattern {pattern}: {e}")
            return 0

    @trace_operation("cache_warm")
    async def warm_cache(self, symbols: Optional[List[str]] = None):
        """
        Pre-populate cache with frequently accessed data.

        This implements cache warming for popular cryptocurrency symbols
        to reduce latency for common requests.

        Args:
            symbols: List of symbols to warm (uses popular_symbols if None)
        """
        symbols_to_warm = symbols or self.popular_symbols

        logger.info(f"Starting cache warming for {len(symbols_to_warm)} symbols...")

        # Import here to avoid circular dependency
        from connectors.price_intelligence.coingecko_connector import CoinGeckoConnector
        from infrastructure.container import get_container

        container = get_container()
        connector = CoinGeckoConnector()

        warmed = 0
        for symbol in symbols_to_warm:
            try:
                # Fetch fresh price data
                price_data = await connector.get_current_price(symbol)

                if price_data:
                    # Cache with standard TTL
                    cache_key = f"price:current:{symbol}"
                    await self.set(
                        key=cache_key,
                        value=price_data,
                        ttl=settings.TTL_LIVE_PRICES,
                        cache_tier="both"
                    )
                    warmed += 1

            except Exception as e:
                logger.warning(f"Failed to warm cache for {symbol}: {e}")

        self.stats['warmings'] += 1
        metrics.increment_counter('cial_cache_warmings_total', value=warmed)

        logger.info(f"Cache warming complete: {warmed}/{len(symbols_to_warm)} symbols cached")

    async def start_warming_task(self):
        """
        Start background task for periodic cache warming.

        This runs continuously and warms the cache at regular intervals
        to ensure popular data is always available with minimal latency.
        """
        logger.info(f"Starting cache warming background task (interval: {self.warming_interval}s)")

        async def warming_loop():
            while True:
                try:
                    await asyncio.sleep(self.warming_interval)
                    await self.warm_cache()
                except asyncio.CancelledError:
                    logger.info("Cache warming task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Cache warming task error: {e}")

        self._warming_task = asyncio.create_task(warming_loop())

    async def stop_warming_task(self):
        """Stop background cache warming task."""
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
            logger.info("Cache warming task stopped")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit/miss rates and operation counts
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'warmings': self.stats['warmings'],
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'warming_interval_seconds': self.warming_interval,
            'popular_symbols': self.popular_symbols
        }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.

    Returns:
        CacheManager: Global cache manager singleton
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cache_key_builder(
    prefix: str,
    *args,
    separator: str = ":",
    include_timestamp: bool = False,
    **kwargs
) -> str:
    """
    Build a standardized cache key from components.

    Args:
        prefix: Key prefix (e.g., "price", "intelligence")
        *args: Positional components
        separator: Key component separator
        include_timestamp: Whether to include timestamp bucket
        **kwargs: Named components

    Returns:
        Formatted cache key

    Examples:
        >>> cache_key_builder("price", "bitcoin", "current")
        'price:bitcoin:current'

        >>> cache_key_builder("intelligence", symbol="ethereum", type="sentiment")
        'intelligence:ethereum:sentiment'
    """
    components = [prefix]

    # Add positional components
    components.extend(str(arg) for arg in args)

    # Add named components (sorted for consistency)
    for key in sorted(kwargs.keys()):
        components.append(f"{key}={kwargs[key]}")

    # Add timestamp bucket if requested (for time-based invalidation)
    if include_timestamp:
        # Bucket by 5-minute intervals
        bucket = int(time.time() // 300) * 300
        components.append(f"t={bucket}")

    return separator.join(components)


def cached(
    ttl: int = 300,
    key_prefix: str = "cached",
    cache_tier: str = "both",
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching function results with cache-aside pattern.

    This implements the cache-aside pattern:
    1. Check cache first
    2. If miss, execute function
    3. Store result in cache
    4. Return result

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_tier: "memory", "redis", or "both"
        key_builder: Custom function to build cache key from args

    Returns:
        Decorated function with caching

    Examples:
        @cached(ttl=300, key_prefix="price")
        async def get_price(symbol: str) -> dict:
            # Expensive API call
            return await api.get_price(symbol)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder: use function name and arguments
                key_parts = [key_prefix, func.__name__]

                # Add args (skip 'self' or 'cls' for methods)
                start_idx = 1 if args and hasattr(args[0], func.__name__) else 0
                key_parts.extend(str(arg) for arg in args[start_idx:])

                # Add kwargs (sorted for consistency)
                for k in sorted(kwargs.keys()):
                    key_parts.append(f"{k}={kwargs[k]}")

                cache_key = ":".join(key_parts)

            # Try to get from cache (cache-aside pattern step 1)
            cached_value = await cache_manager.get(cache_key, cache_tier=cache_tier)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_value

            # Cache miss - execute function (cache-aside pattern step 2)
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache (cache-aside pattern step 3)
            if result is not None:
                await cache_manager.set(
                    key=cache_key,
                    value=result,
                    ttl=ttl,
                    cache_tier=cache_tier
                )

            # Return result (cache-aside pattern step 4)
            return result

        return wrapper
    return decorator


# Cache invalidation strategies
class CacheInvalidationStrategy:
    """
    Smart cache invalidation strategies for different use cases.
    """

    @staticmethod
    async def invalidate_on_write(key: str):
        """
        Simple invalidation: delete cache key when data is written.

        Use for: Data that changes infrequently
        """
        cache_manager = get_cache_manager()
        await cache_manager.delete(key)

    @staticmethod
    async def invalidate_related_keys(base_key: str, related_patterns: List[str]):
        """
        Invalidate base key and all related keys.

        Use for: Data with dependencies (e.g., updating BTC price invalidates BTC/USD pair)

        Args:
            base_key: Primary key to invalidate
            related_patterns: List of patterns for related keys
        """
        cache_manager = get_cache_manager()

        # Invalidate base key
        await cache_manager.delete(base_key)

        # Invalidate related keys
        for pattern in related_patterns:
            await cache_manager.invalidate_pattern(pattern)

    @staticmethod
    async def time_based_invalidation(pattern: str, max_age_seconds: int):
        """
        Invalidate keys older than a certain age.

        Use for: Time-sensitive data (e.g., price data older than 1 hour)

        Args:
            pattern: Key pattern to check
            max_age_seconds: Maximum age before invalidation
        """
        # This would require storing timestamps with cache entries
        # Implementation would check entry age and delete if too old
        pass

    @staticmethod
    async def cache_refresh(key: str, refresh_func: Callable, ttl: int):
        """
        Refresh cache entry with fresh data (cache refresh pattern).

        Use for: Keeping cache warm with latest data

        Args:
            key: Cache key to refresh
            refresh_func: Function to fetch fresh data
            ttl: New TTL for refreshed data
        """
        cache_manager = get_cache_manager()

        # Fetch fresh data
        fresh_data = await refresh_func()

        # Update cache
        if fresh_data is not None:
            await cache_manager.set(key, fresh_data, ttl=ttl)
