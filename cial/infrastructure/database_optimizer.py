"""
CIAL Database Optimization
Session 19: Advanced PostgreSQL optimization for high-performance queries

Features:
- Intelligent index management
- Materialized views for complex queries
- Connection pooling optimization
- Query performance monitoring
- Automatic EXPLAIN ANALYZE
- Index usage statistics
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.observability import metrics, trace_operation


class DatabaseOptimizer:
    """
    Manages database optimizations including indexes, materialized views,
    and query performance monitoring.
    """

    def __init__(self, postgres_manager):
        """
        Initialize database optimizer.

        Args:
            postgres_manager: PostgresManager instance
        """
        self.postgres_manager = postgres_manager
        self.query_stats: dict[str, dict[str, Any]] = {}

    @trace_operation("db_create_indexes")
    async def create_performance_indexes(self):
        """
        Create optimized indexes for common query patterns.

        Indexes improve query performance by 10-1000x for filtered queries.
        """
        logger.info("Creating performance indexes...")

        indexes = [
            # Intelligence records indexes
            {
                "name": "idx_intelligence_symbol",
                "table": "intelligence_records",
                "columns": ["symbol"],
                "description": "Fast symbol lookup",
            },
            {
                "name": "idx_intelligence_type",
                "table": "intelligence_records",
                "columns": ["intelligence_type"],
                "description": "Filter by intelligence type",
            },
            {
                "name": "idx_intelligence_timestamp",
                "table": "intelligence_records",
                "columns": ["timestamp DESC"],
                "description": "Time-based queries (latest first)",
            },
            {
                "name": "idx_intelligence_symbol_timestamp",
                "table": "intelligence_records",
                "columns": ["symbol", "timestamp DESC"],
                "description": "Symbol + time queries (composite)",
            },
            {
                "name": "idx_intelligence_symbol_type",
                "table": "intelligence_records",
                "columns": ["symbol", "intelligence_type"],
                "description": "Symbol + type queries (composite)",
            },
            {
                "name": "idx_intelligence_timestamp_type",
                "table": "intelligence_records",
                "columns": ["timestamp DESC", "intelligence_type"],
                "description": "Time + type queries (composite)",
            },
            # Agent memory indexes
            {
                "name": "idx_agent_memory_agent_id",
                "table": "agent_memory",
                "columns": ["agent_id"],
                "description": "Fast agent lookup",
            },
            {
                "name": "idx_agent_memory_context_type",
                "table": "agent_memory",
                "columns": ["context_type"],
                "description": "Filter by context type",
            },
            {
                "name": "idx_agent_memory_created_at",
                "table": "agent_memory",
                "columns": ["created_at DESC"],
                "description": "Time-based agent memory queries",
            },
            # Validation records indexes
            {
                "name": "idx_validation_symbol",
                "table": "validation_records",
                "columns": ["symbol"],
                "description": "Fast validation lookup by symbol",
            },
            {
                "name": "idx_validation_timestamp",
                "table": "validation_records",
                "columns": ["timestamp DESC"],
                "description": "Recent validation queries",
            },
        ]

        created = 0
        for index in indexes:
            try:
                columns_str = ", ".join(index["columns"])
                sql = f"""
                CREATE INDEX IF NOT EXISTS {index["name"]}
                ON {index["table"]} ({columns_str})
                """

                await self.postgres_manager.execute_query(sql)
                logger.info(f"✅ Created index: {index['name']} - {index['description']}")
                created += 1

            except Exception as e:
                logger.error(f"Failed to create index {index['name']}: {e}")

        logger.info(f"Created {created}/{len(indexes)} indexes")

        metrics.increment_counter("cial_database_indexes_created_total", value=created)

        return created

    @trace_operation("db_create_materialized_views")
    async def create_materialized_views(self):
        """
        Create materialized views for expensive queries.

        Materialized views pre-compute complex queries for instant access.
        """
        logger.info("Creating materialized views...")

        views = [
            {
                "name": "mv_symbol_statistics",
                "description": "Pre-computed symbol statistics",
                "sql": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_symbol_statistics AS
                SELECT
                    symbol,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT intelligence_type) as intelligence_types,
                    MAX(timestamp) as latest_update,
                    MIN(timestamp) as first_seen,
                    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) as age_seconds
                FROM intelligence_records
                GROUP BY symbol
                WITH DATA
                """,
            },
            {
                "name": "mv_intelligence_type_summary",
                "description": "Summary by intelligence type",
                "sql": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_intelligence_type_summary AS
                SELECT
                    intelligence_type,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    MAX(timestamp) as latest_update,
                    AVG(EXTRACT(EPOCH FROM (NOW() - timestamp))) as avg_age_seconds
                FROM intelligence_records
                GROUP BY intelligence_type
                WITH DATA
                """,
            },
            {
                "name": "mv_daily_intelligence_counts",
                "description": "Daily intelligence record counts",
                "sql": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_intelligence_counts AS
                SELECT
                    DATE(timestamp) as date,
                    intelligence_type,
                    symbol,
                    COUNT(*) as record_count
                FROM intelligence_records
                WHERE timestamp >= NOW() - INTERVAL '90 days'
                GROUP BY DATE(timestamp), intelligence_type, symbol
                WITH DATA
                """,
            },
            {
                "name": "mv_agent_activity_summary",
                "description": "Agent activity statistics",
                "sql": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_agent_activity_summary AS
                SELECT
                    agent_id,
                    COUNT(*) as total_memories,
                    COUNT(DISTINCT context_type) as context_types,
                    MAX(created_at) as last_active,
                    MAX(accessed_at) as last_accessed
                FROM agent_memory
                GROUP BY agent_id
                WITH DATA
                """,
            },
        ]

        created = 0
        for view in views:
            try:
                # Drop if exists (for updates)
                await self.postgres_manager.execute_query(
                    f"DROP MATERIALIZED VIEW IF EXISTS {view['name']} CASCADE"
                )

                # Create materialized view
                await self.postgres_manager.execute_query(view["sql"])

                # Create index on materialized view
                await self.postgres_manager.execute_query(
                    f"CREATE INDEX IF NOT EXISTS idx_{view['name']}_refresh "
                    f"ON {view['name']} (1)"
                )

                logger.info(f"✅ Created materialized view: {view['name']} - {view['description']}")
                created += 1

            except Exception as e:
                logger.error(f"Failed to create materialized view {view['name']}: {e}")

        logger.info(f"Created {created}/{len(views)} materialized views")

        metrics.increment_counter("cial_database_materialized_views_created_total", value=created)

        return created

    @trace_operation("db_refresh_materialized_views")
    async def refresh_materialized_views(self, concurrent: bool = True):
        """
        Refresh all materialized views with latest data.

        Args:
            concurrent: If True, refresh concurrently (doesn't block reads)

        Returns:
            Number of views refreshed
        """
        logger.info("Refreshing materialized views...")

        views = [
            "mv_symbol_statistics",
            "mv_intelligence_type_summary",
            "mv_daily_intelligence_counts",
            "mv_agent_activity_summary",
        ]

        refreshed = 0
        for view_name in views:
            try:
                refresh_mode = "CONCURRENTLY" if concurrent else ""
                sql = f"REFRESH MATERIALIZED VIEW {refresh_mode} {view_name}"

                start_time = time.time()
                await self.postgres_manager.execute_query(sql)
                duration = time.time() - start_time

                logger.info(f"✅ Refreshed {view_name} in {duration:.2f}s")
                refreshed += 1

                metrics.record_histogram(
                    "cial_database_mv_refresh_seconds", duration, {"view": view_name}
                )

            except Exception as e:
                logger.error(f"Failed to refresh materialized view {view_name}: {e}")

        logger.info(f"Refreshed {refreshed}/{len(views)} materialized views")

        return refreshed

    @trace_operation("db_analyze_query")
    async def analyze_query(self, query: str) -> dict[str, Any]:
        """
        Analyze query performance using EXPLAIN ANALYZE.

        Args:
            query: SQL query to analyze

        Returns:
            Query execution plan and statistics
        """
        try:
            # Run EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"

            start_time = time.time()
            result = await self.postgres_manager.fetch_one(explain_query)
            duration = time.time() - start_time

            if result:
                plan = result[0]  # JSON plan

                analysis = {
                    "query": query,
                    "execution_time_ms": duration * 1000,
                    "plan": plan,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Store query stats
                query_hash = str(hash(query))
                if query_hash not in self.query_stats:
                    self.query_stats[query_hash] = {
                        "query": query,
                        "executions": 0,
                        "total_time_ms": 0,
                        "avg_time_ms": 0,
                        "min_time_ms": float("inf"),
                        "max_time_ms": 0,
                    }

                stats = self.query_stats[query_hash]
                stats["executions"] += 1
                stats["total_time_ms"] += duration * 1000
                stats["avg_time_ms"] = stats["total_time_ms"] / stats["executions"]
                stats["min_time_ms"] = min(stats["min_time_ms"], duration * 1000)
                stats["max_time_ms"] = max(stats["max_time_ms"], duration * 1000)

                return analysis

            return {"error": "No result from EXPLAIN ANALYZE"}

        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {"error": str(e)}

    @trace_operation("db_get_index_usage")
    async def get_index_usage_stats(self) -> list[dict[str, Any]]:
        """
        Get index usage statistics.

        Returns:
            List of indexes with usage statistics
        """
        query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC
        """

        try:
            results = await self.postgres_manager.fetch_all(query)
            return [dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Failed to get index usage stats: {e}")
            return []

    @trace_operation("db_get_table_stats")
    async def get_table_stats(self) -> list[dict[str, Any]]:
        """
        Get table statistics including size and row counts.

        Returns:
            List of tables with statistics
        """
        query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                          pg_relation_size(schemaname||'.'||tablename)) as indexes_size,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """

        try:
            results = await self.postgres_manager.fetch_all(query)
            return [dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return []

    @trace_operation("db_vacuum_analyze")
    async def vacuum_analyze_tables(self, tables: list[str] | None = None):
        """
        Run VACUUM ANALYZE on tables to update statistics and reclaim space.

        Args:
            tables: List of table names (None = all tables)
        """
        if tables is None:
            # Get all user tables
            query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            results = await self.postgres_manager.fetch_all(query)
            tables = [row[0] for row in results] if results else []

        logger.info(f"Running VACUUM ANALYZE on {len(tables)} tables...")

        for table in tables:
            try:
                await self.postgres_manager.execute_query(f"VACUUM ANALYZE {table}")
                logger.info(f"✅ VACUUM ANALYZE completed for {table}")

            except Exception as e:
                logger.error(f"VACUUM ANALYZE failed for {table}: {e}")

        logger.info("VACUUM ANALYZE complete")

    def get_slow_queries(self, min_duration_ms: float = 1000) -> list[dict[str, Any]]:
        """
        Get queries slower than threshold.

        Args:
            min_duration_ms: Minimum duration in milliseconds

        Returns:
            List of slow queries with statistics
        """
        slow_queries = []

        for query_hash, stats in self.query_stats.items():
            if stats["avg_time_ms"] >= min_duration_ms:
                slow_queries.append(stats)

        return sorted(slow_queries, key=lambda x: x["avg_time_ms"], reverse=True)

    def get_query_stats_summary(self) -> dict[str, Any]:
        """
        Get summary of query statistics.

        Returns:
            Summary statistics
        """
        if not self.query_stats:
            return {"total_queries": 0, "total_executions": 0, "avg_query_time_ms": 0}

        total_executions = sum(s["executions"] for s in self.query_stats.values())
        total_time = sum(s["total_time_ms"] for s in self.query_stats.values())

        return {
            "total_unique_queries": len(self.query_stats),
            "total_executions": total_executions,
            "total_time_ms": total_time,
            "avg_query_time_ms": total_time / total_executions if total_executions > 0 else 0,
            "queries": list(self.query_stats.values()),
        }


# Global optimizer instance
_db_optimizer: DatabaseOptimizer | None = None


async def get_database_optimizer() -> DatabaseOptimizer:
    """
    Get the global database optimizer instance.

    Returns:
        DatabaseOptimizer: Global optimizer
    """
    global _db_optimizer
    if _db_optimizer is None:
        from infrastructure.container import get_container

        container = get_container()
        postgres_manager = container.postgres_manager()
        _db_optimizer = DatabaseOptimizer(postgres_manager)

    return _db_optimizer
