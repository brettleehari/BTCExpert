"""
CIAL Cache Management API
Session 17: Caching Layer Enhancement

Endpoints for cache monitoring, warming, and invalidation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.responses import VersionedResponse, error_response, success_response
from infrastructure.caching import cache_key_builder, get_cache_manager
from infrastructure.logging_config import logger
from infrastructure.observability import trace_operation

router = APIRouter()


@router.get("/stats")
@trace_operation("cache_stats")
async def get_cache_stats() -> VersionedResponse[Dict[str, Any]]:
    """
    Get cache statistics including hit/miss rates.

    Returns detailed cache performance metrics:
    - Total hits and misses
    - Cache hit rate percentage
    - Number of sets, deletes, and warmings
    - Cache warming configuration

    Returns:
        Cache statistics and performance metrics
    """
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_stats()

        return success_response(data=stats, message="Cache statistics retrieved successfully")

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve cache statistics",
            error_code="CACHE_STATS_ERROR",
            details={"error": str(e)},
        )


@router.post("/warm")
@trace_operation("cache_warm")
async def warm_cache(
    symbols: Optional[List[str]] = Query(
        None, description="Specific symbols to warm (uses popular symbols if not provided)"
    )
) -> VersionedResponse[Dict[str, Any]]:
    """
    Trigger cache warming for specified symbols.

    Cache warming pre-populates the cache with frequently accessed data
    to reduce latency for common requests. This is useful after:
    - Cache invalidation
    - System restart
    - Adding new popular symbols

    Args:
        symbols: List of cryptocurrency symbols to warm cache for

    Returns:
        Cache warming results
    """
    try:
        cache_manager = get_cache_manager()

        # Trigger cache warming
        await cache_manager.warm_cache(symbols=symbols)

        return success_response(
            data={
                "warmed_symbols": symbols or cache_manager.popular_symbols,
                "timestamp": datetime.utcnow().isoformat(),
            },
            message="Cache warming completed successfully",
        )

    except Exception as e:
        logger.error(f"Cache warming failed: {e}", exc_info=True)
        return error_response(
            message="Cache warming failed", error_code="CACHE_WARM_ERROR", details={"error": str(e)}
        )


@router.delete("/invalidate/{key}")
@trace_operation("cache_invalidate_key")
async def invalidate_cache_key(
    key: str,
    cache_tier: str = Query(
        "both", description="Cache tier to invalidate: 'memory', 'redis', or 'both'"
    ),
) -> VersionedResponse[Dict[str, Any]]:
    """
    Invalidate a specific cache key.

    Removes the specified key from cache, forcing fresh data fetch
    on next request. Useful for:
    - Manual cache invalidation after data updates
    - Clearing stale data
    - Testing cache behavior

    Args:
        key: Cache key to invalidate
        cache_tier: Which cache tier to invalidate from

    Returns:
        Invalidation result
    """
    try:
        cache_manager = get_cache_manager()
        success = await cache_manager.delete(key, cache_tier=cache_tier)

        if success:
            return success_response(
                data={"key": key, "cache_tier": cache_tier, "invalidated": True},
                message=f"Cache key '{key}' invalidated successfully",
            )
        else:
            return error_response(
                message=f"Failed to invalidate cache key '{key}'", error_code="INVALIDATION_FAILED"
            )

    except Exception as e:
        logger.error(f"Cache invalidation failed for key {key}: {e}", exc_info=True)
        return error_response(
            message="Cache invalidation failed",
            error_code="CACHE_INVALIDATE_ERROR",
            details={"error": str(e)},
        )


@router.delete("/invalidate/pattern/{pattern}")
@trace_operation("cache_invalidate_pattern")
async def invalidate_cache_pattern(pattern: str) -> VersionedResponse[Dict[str, Any]]:
    """
    Invalidate all cache keys matching a pattern.

    Uses Redis pattern matching to invalidate multiple related keys:
    - price:* - All price data
    - intelligence:bitcoin:* - All Bitcoin intelligence
    - *:ethereum:* - All Ethereum-related data

    Args:
        pattern: Redis key pattern (supports * and ? wildcards)

    Returns:
        Number of keys invalidated

    Examples:
        - Pattern: "price:*" - Invalidates all price cache
        - Pattern: "intelligence:bitcoin:*" - Invalidates Bitcoin intelligence
    """
    try:
        cache_manager = get_cache_manager()
        deleted_count = await cache_manager.invalidate_pattern(pattern)

        return success_response(
            data={"pattern": pattern, "keys_deleted": deleted_count},
            message=f"Invalidated {deleted_count} keys matching pattern '{pattern}'",
        )

    except Exception as e:
        logger.error(f"Pattern invalidation failed for {pattern}: {e}", exc_info=True)
        return error_response(
            message="Pattern invalidation failed",
            error_code="PATTERN_INVALIDATE_ERROR",
            details={"error": str(e)},
        )


@router.get("/get/{key}")
@trace_operation("cache_get_api")
async def get_cache_value(
    key: str,
    cache_tier: str = Query(
        "both", description="Cache tier to query: 'memory', 'redis', or 'both'"
    ),
) -> VersionedResponse[Dict[str, Any]]:
    """
    Get value from cache (for debugging/monitoring).

    Retrieves cached value for inspection. Useful for:
    - Debugging cache behavior
    - Verifying cached data
    - Cache inspection during development

    Args:
        key: Cache key to retrieve
        cache_tier: Which cache tier to query

    Returns:
        Cached value or None if not found
    """
    try:
        cache_manager = get_cache_manager()
        value = await cache_manager.get(key, cache_tier=cache_tier)

        if value is not None:
            return success_response(
                data={"key": key, "value": value, "found": True, "cache_tier": cache_tier},
                message="Cache value retrieved",
            )
        else:
            return success_response(
                data={"key": key, "value": None, "found": False, "cache_tier": cache_tier},
                message="Cache key not found",
            )

    except Exception as e:
        logger.error(f"Failed to get cache value for key {key}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve cache value",
            error_code="CACHE_GET_ERROR",
            details={"error": str(e)},
        )


@router.post("/set")
@trace_operation("cache_set_api")
async def set_cache_value(
    key: str = Query(..., description="Cache key"),
    value: Any = Query(..., description="Value to cache"),
    ttl: Optional[int] = Query(None, description="Time-to-live in seconds"),
    cache_tier: str = Query("both", description="Cache tier: 'memory', 'redis', or 'both'"),
) -> VersionedResponse[Dict[str, Any]]:
    """
    Set value in cache (for testing/development).

    Manually set a cache value. Useful for:
    - Testing cache behavior
    - Pre-populating cache with specific data
    - Development and debugging

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (None = no expiry)
        cache_tier: Which cache tier to set

    Returns:
        Set operation result
    """
    try:
        cache_manager = get_cache_manager()
        success = await cache_manager.set(key=key, value=value, ttl=ttl, cache_tier=cache_tier)

        if success:
            return success_response(
                data={"key": key, "ttl": ttl, "cache_tier": cache_tier, "set": True},
                message="Cache value set successfully",
            )
        else:
            return error_response(
                message="Failed to set cache value", error_code="CACHE_SET_FAILED"
            )

    except Exception as e:
        logger.error(f"Failed to set cache value for key {key}: {e}", exc_info=True)
        return error_response(
            message="Failed to set cache value",
            error_code="CACHE_SET_ERROR",
            details={"error": str(e)},
        )


@router.get("/health")
async def cache_health() -> VersionedResponse[Dict[str, str]]:
    """
    Check cache layer health status.

    Verifies that both memory and Redis caches are operational.

    Returns:
        Cache layer health status
    """
    try:
        cache_manager = get_cache_manager()

        # Test memory cache
        test_key = "health_check_test"
        await cache_manager.memory_cache.set(test_key, "ok", ttl=10)
        memory_ok = await cache_manager.memory_cache.get(test_key) == "ok"
        await cache_manager.memory_cache.delete(test_key)

        # Test Redis cache
        await cache_manager.redis_cache.set(test_key, "ok", ttl=10)
        redis_ok = await cache_manager.redis_cache.get(test_key) == "ok"
        await cache_manager.redis_cache.delete(test_key)

        status = "healthy" if (memory_ok and redis_ok) else "degraded"

        return success_response(
            data={
                "status": status,
                "memory_cache": "operational" if memory_ok else "failed",
                "redis_cache": "operational" if redis_ok else "failed",
                "timestamp": datetime.utcnow().isoformat(),
            },
            message=f"Cache layer is {status}",
        )

    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        return error_response(
            message="Cache health check failed",
            error_code="CACHE_HEALTH_ERROR",
            details={"error": str(e)},
        )
