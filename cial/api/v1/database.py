"""
CIAL Database Optimization API
Session 19: Database performance management and monitoring

Endpoints for database optimization, statistics, and health.
"""

from typing import Any

from api.models.responses import VersionedResponse, error_response, success_response
from fastapi import APIRouter, Query
from infrastructure.database_optimizer import get_database_optimizer
from infrastructure.logging_config import logger
from infrastructure.observability import trace_operation

router = APIRouter()


@router.post("/optimize/indexes")
@trace_operation("db_create_indexes")
async def create_indexes() -> VersionedResponse[dict[str, Any]]:
    """
    Create performance indexes on database tables.

    Creates optimized indexes for common query patterns:
    - Symbol lookups
    - Time-range queries
    - Intelligence type filtering
    - Composite indexes for multi-column queries

    **Impact:** 10-1000x faster queries on indexed columns

    Returns:
        Number of indexes created
    """
    try:
        optimizer = await get_database_optimizer()
        created = await optimizer.create_performance_indexes()

        return success_response(
            data={"indexes_created": created}, message=f"Created {created} performance indexes"
        )

    except Exception as e:
        logger.error(f"Failed to create indexes: {e}", exc_info=True)
        return error_response(
            message="Failed to create indexes",
            error_code="INDEX_CREATION_ERROR",
            details={"error": str(e)},
        )


@router.post("/optimize/materialized-views")
@trace_operation("db_create_materialized_views")
async def create_materialized_views() -> VersionedResponse[dict[str, Any]]:
    """
    Create materialized views for expensive queries.

    Materialized views pre-compute complex aggregations:
    - Symbol statistics
    - Intelligence type summaries
    - Daily counts
    - Agent activity summaries

    **Impact:** 100-10000x faster complex queries

    Returns:
        Number of materialized views created
    """
    try:
        optimizer = await get_database_optimizer()
        created = await optimizer.create_materialized_views()

        return success_response(
            data={"materialized_views_created": created},
            message=f"Created {created} materialized views",
        )

    except Exception as e:
        logger.error(f"Failed to create materialized views: {e}", exc_info=True)
        return error_response(
            message="Failed to create materialized views",
            error_code="MATERIALIZED_VIEW_CREATION_ERROR",
            details={"error": str(e)},
        )


@router.post("/optimize/refresh-views")
@trace_operation("db_refresh_materialized_views")
async def refresh_materialized_views(
    concurrent: bool = Query(
        True, description="Refresh concurrently (doesn't block reads)"
    )  # noqa: B008
) -> VersionedResponse[dict[str, Any]]:
    """
    Refresh materialized views with latest data.

    Should be run periodically (e.g., every hour) to keep
    materialized views up-to-date.

    Args:
        concurrent: If True, refreshes don't block reads (slower but non-blocking)

    Returns:
        Number of views refreshed
    """
    try:
        optimizer = await get_database_optimizer()
        refreshed = await optimizer.refresh_materialized_views(concurrent=concurrent)

        return success_response(
            data={"views_refreshed": refreshed, "concurrent": concurrent},
            message=f"Refreshed {refreshed} materialized views",
        )

    except Exception as e:
        logger.error(f"Failed to refresh materialized views: {e}", exc_info=True)
        return error_response(
            message="Failed to refresh materialized views",
            error_code="MATERIALIZED_VIEW_REFRESH_ERROR",
            details={"error": str(e)},
        )


@router.post("/optimize/vacuum")
@trace_operation("db_vacuum_analyze")
async def vacuum_analyze(
    tables: list[str] | None = Query(  # noqa: B008
        None, description="Specific tables to vacuum (None = all tables)"
    )
) -> VersionedResponse[dict[str, str]]:
    """
    Run VACUUM ANALYZE on tables.

    VACUUM ANALYZE:
    - Reclaims storage from dead tuples
    - Updates table statistics for query planner
    - Improves query performance

    **When to run:**
    - After bulk inserts/updates/deletes
    - When query performance degrades
    - Periodically (weekly)

    Args:
        tables: List of table names (None = all tables)

    Returns:
        Vacuum completion status
    """
    try:
        optimizer = await get_database_optimizer()
        await optimizer.vacuum_analyze_tables(tables=tables)

        return success_response(
            data={"status": "completed"}, message="VACUUM ANALYZE completed successfully"
        )

    except Exception as e:
        logger.error(f"VACUUM ANALYZE failed: {e}", exc_info=True)
        return error_response(
            message="VACUUM ANALYZE failed", error_code="VACUUM_ERROR", details={"error": str(e)}
        )


@router.post("/analyze/query")
@trace_operation("db_analyze_query")
async def analyze_query(query: str) -> VersionedResponse[dict[str, Any]]:
    """
    Analyze query performance using EXPLAIN ANALYZE.

    Returns detailed query execution plan including:
    - Execution time
    - Index usage
    - Row counts
    - Buffer usage
    - Query plan tree

    **Use for:**
    - Debugging slow queries
    - Optimizing query structure
    - Verifying index usage

    Args:
        query: SQL query to analyze (SELECT only)

    Returns:
        Query execution plan and statistics

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/database/analyze/query" \
          -H "Content-Type: application/json" \
          -d '{"query": "SELECT * FROM intelligence_records WHERE symbol = '\''bitcoin'\'' LIMIT 10"}'
        ```
    """
    try:
        # Safety check: only allow SELECT queries
        if not query.strip().upper().startswith("SELECT"):
            return error_response(
                message="Only SELECT queries are allowed for analysis",
                error_code="INVALID_QUERY_TYPE",
            )

        optimizer = await get_database_optimizer()
        analysis = await optimizer.analyze_query(query)

        if "error" in analysis:
            return error_response(
                message="Query analysis failed", error_code="QUERY_ANALYSIS_ERROR", details=analysis
            )

        return success_response(data=analysis, message="Query analyzed successfully")

    except Exception as e:
        logger.error(f"Query analysis failed: {e}", exc_info=True)
        return error_response(
            message="Query analysis failed",
            error_code="QUERY_ANALYSIS_ERROR",
            details={"error": str(e)},
        )


@router.get("/stats/indexes")
@trace_operation("db_index_usage_stats")
async def get_index_usage() -> VersionedResponse[list[dict[str, Any]]]:
    """
    Get index usage statistics.

    Returns:
        List of indexes with usage metrics including:
        - Index scans
        - Tuples read/fetched
        - Index size

    **Use to identify:**
    - Unused indexes (candidates for removal)
    - Most used indexes
    - Index effectiveness
    """
    try:
        optimizer = await get_database_optimizer()
        stats = await optimizer.get_index_usage_stats()

        return success_response(
            data={"indexes": stats, "total_indexes": len(stats)},
            message="Index usage statistics retrieved",
        )

    except Exception as e:
        logger.error(f"Failed to get index usage stats: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve index usage statistics",
            error_code="INDEX_STATS_ERROR",
            details={"error": str(e)},
        )


@router.get("/stats/tables")
@trace_operation("db_table_stats")
async def get_table_stats() -> VersionedResponse[list[dict[str, Any]]]:
    """
    Get table statistics.

    Returns:
        List of tables with statistics including:
        - Table and index sizes
        - Row counts (live/dead tuples)
        - Insert/update/delete counts
        - Last vacuum/analyze timestamps

    **Use to identify:**
    - Large tables needing optimization
    - Tables with many dead tuples (need VACUUM)
    - Tables needing ANALYZE
    """
    try:
        optimizer = await get_database_optimizer()
        stats = await optimizer.get_table_stats()

        return success_response(
            data={"tables": stats, "total_tables": len(stats)}, message="Table statistics retrieved"
        )

    except Exception as e:
        logger.error(f"Failed to get table stats: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve table statistics",
            error_code="TABLE_STATS_ERROR",
            details={"error": str(e)},
        )


@router.get("/stats/queries")
@trace_operation("db_query_stats")
async def get_query_stats(
    min_duration_ms: float = Query(
        0, description="Only show queries slower than this (ms)"
    )  # noqa: B008
) -> VersionedResponse[dict[str, Any]]:
    """
    Get query performance statistics.

    Returns statistics for all queries executed through the optimizer:
    - Total executions
    - Average/min/max execution times
    - Slow queries

    Args:
        min_duration_ms: Filter for queries slower than threshold

    Returns:
        Query statistics and slow queries list

    **Use to identify:**
    - Slow queries needing optimization
    - Frequently executed queries
    - Query performance trends
    """
    try:
        optimizer = await get_database_optimizer()

        if min_duration_ms > 0:
            slow_queries = optimizer.get_slow_queries(min_duration_ms=min_duration_ms)
            return success_response(
                data={
                    "slow_queries": slow_queries,
                    "threshold_ms": min_duration_ms,
                    "count": len(slow_queries),
                },
                message=f"Found {len(slow_queries)} slow queries",
            )
        else:
            summary = optimizer.get_query_stats_summary()
            return success_response(data=summary, message="Query statistics retrieved")

    except Exception as e:
        logger.error(f"Failed to get query stats: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve query statistics",
            error_code="QUERY_STATS_ERROR",
            details={"error": str(e)},
        )


@router.get("/health")
async def database_health() -> VersionedResponse[dict[str, Any]]:
    """
    Check database optimization health.

    Returns:
        Database health metrics including:
        - Index count
        - Materialized view count
        - Query statistics
        - Connection pool status
    """
    try:
        optimizer = await get_database_optimizer()

        # Get index count
        index_stats = await optimizer.get_index_usage_stats()

        # Get table stats
        table_stats = await optimizer.get_table_stats()

        # Get query stats
        query_summary = optimizer.get_query_stats_summary()

        return success_response(
            data={
                "status": "healthy",
                "indexes": len(index_stats),
                "tables": len(table_stats),
                "queries_tracked": query_summary.get("total_unique_queries", 0),
                "avg_query_time_ms": query_summary.get("avg_query_time_ms", 0),
            },
            message="Database optimization is healthy",
        )

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return error_response(
            message="Database health check failed",
            error_code="DB_HEALTH_ERROR",
            details={"error": str(e)},
        )
