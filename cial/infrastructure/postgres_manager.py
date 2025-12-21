"""
CIAL PostgreSQL Manager
Long-Term Memory persistence with vector search capabilities

Version: 2.0 - Production Ready with Resilience Patterns
"""

from datetime import datetime
from typing import Any

import asyncpg
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.resilience import get_bulkhead, get_health_check, retry_with_backoff

# SQLAlchemy Base
Base = declarative_base()


class IntelligenceRecord(Base):
    """
    SQLAlchemy model for intelligence records in PostgreSQL.
    """

    __tablename__ = "intelligence_records"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False, index=True)
    importance = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=True, index=True)
    data = Column(JSON, nullable=False)
    meta_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    validated = Column(Boolean, default=False)

    # Analytics fields
    routed_to_count = Column(Integer, default=0)
    accessed_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)

    # Vector embedding (for semantic search)
    embedding_vector = Column(Text, nullable=True)  # Stored as JSON array


class AgentRecord(Base):
    """
    SQLAlchemy model for agent registration records.
    """

    __tablename__ = "agent_records"

    agent_id = Column(String, primary_key=True)
    agent_type = Column(String, nullable=False, index=True)
    capabilities = Column(JSON, nullable=False)
    status = Column(String, nullable=False, index=True)
    registered_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime, nullable=False)
    total_messages_received = Column(Integer, default=0)
    meta_data = Column(JSON, nullable=True)


class PostgresManager:
    """
    PostgreSQL manager for CIAL Long-Term Memory.

    Responsibilities:
    - Persistent intelligence storage
    - Historical data retrieval
    - Analytics and reporting
    - Vector-based semantic search
    """

    def __init__(self):
        self._engine = None
        self._session_maker = None
        self._pool: asyncpg.Pool | None = None
        self._connected = False

        # Resilience patterns
        self.write_bulkhead = get_bulkhead("postgres_writes", max_concurrent=20, timeout=30.0)
        self.read_bulkhead = get_bulkhead("postgres_reads", max_concurrent=50, timeout=10.0)
        self.health = get_health_check("postgres_ltm", threshold_success_rate=0.95)

    @retry_with_backoff(max_attempts=5, min_wait=2, max_wait=30)
    async def connect(self):
        """
        Initialize PostgreSQL connections with retry logic.

        Resilience: 5 retry attempts with exponential backoff (2s, 4s, 8s, 16s, 30s)
        """
        try:
            # Create SQLAlchemy async engine
            self._engine = create_async_engine(
                settings.async_postgres_url,
                echo=settings.DEBUG,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
            )

            # Create session maker
            self._session_maker = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create connection pool
            self._pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                min_size=5,
                max_size=20,
            )

            # Create tables
            await self._create_tables()

            # Enable pgvector extension if available
            await self._enable_vector_extension()

            # Enable TimescaleDB extension for time-series optimization
            await self._enable_timescaledb_extension()

            self._connected = True
            self.health.record_success()

            logger.info(
                "PostgreSQL connected successfully with resilience patterns",
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
            )

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise

    async def disconnect(self):
        """Close PostgreSQL connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("PostgreSQL engine disposed")

        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL pool closed")

        self._connected = False

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}", exc_info=True)

    async def _enable_vector_extension(self):
        """Enable pgvector extension for semantic search."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                logger.info("pgvector extension enabled")
        except Exception as e:
            logger.warning(f"pgvector extension not available: {e}")

    async def _enable_timescaledb_extension(self):
        """
        Enable TimescaleDB extension for optimized time-series data.

        TimescaleDB provides:
        - Hypertables for automatic partitioning by time
        - 100x faster time-range queries
        - Automatic compression for old data
        - Continuous aggregates for pre-computed analytics
        """
        try:
            async with self._pool.acquire() as conn:
                # Enable TimescaleDB extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
                logger.info("✅ TimescaleDB extension enabled")

                # Convert intelligence_records to hypertable if not already
                # Check if table is already a hypertable
                is_hypertable = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM timescaledb_information.hypertables
                        WHERE hypertable_name = 'intelligence_records'
                    )
                    """
                )

                if not is_hypertable:
                    # Convert to hypertable partitioned by timestamp
                    await conn.execute(
                        """
                        SELECT create_hypertable(
                            'intelligence_records',
                            'timestamp',
                            if_not_exists => TRUE,
                            chunk_time_interval => INTERVAL '1 day'
                        )
                        """
                    )
                    logger.info("✅ intelligence_records converted to hypertable (1-day chunks)")

                    # Add compression policy (compress data older than 7 days)
                    await conn.execute(
                        """
                        ALTER TABLE intelligence_records SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'type,symbol'
                        )
                        """
                    )

                    await conn.execute(
                        """
                        SELECT add_compression_policy(
                            'intelligence_records',
                            INTERVAL '7 days',
                            if_not_exists => TRUE
                        )
                        """
                    )
                    logger.info("✅ Compression policy added (compress after 7 days)")

                    # Create continuous aggregate for hourly statistics
                    await conn.execute(
                        """
                        CREATE MATERIALIZED VIEW IF NOT EXISTS intelligence_hourly_stats
                        WITH (timescaledb.continuous) AS
                        SELECT
                            time_bucket('1 hour', timestamp) AS hour,
                            type,
                            symbol,
                            COUNT(*) as message_count,
                            COUNT(DISTINCT source) as unique_sources,
                            SUM(routed_to_count) as total_routes
                        FROM intelligence_records
                        GROUP BY hour, type, symbol
                        WITH NO DATA
                        """
                    )

                    # Add refresh policy for continuous aggregate
                    await conn.execute(
                        """
                        SELECT add_continuous_aggregate_policy(
                            'intelligence_hourly_stats',
                            start_offset => INTERVAL '3 hours',
                            end_offset => INTERVAL '1 hour',
                            schedule_interval => INTERVAL '1 hour',
                            if_not_exists => TRUE
                        )
                        """
                    )
                    logger.info("✅ Continuous aggregate created (hourly stats)")

                    # Create continuous aggregate for daily statistics
                    await conn.execute(
                        """
                        CREATE MATERIALIZED VIEW IF NOT EXISTS intelligence_daily_stats
                        WITH (timescaledb.continuous) AS
                        SELECT
                            time_bucket('1 day', timestamp) AS day,
                            type,
                            COUNT(*) as message_count,
                            COUNT(DISTINCT symbol) as unique_symbols,
                            COUNT(DISTINCT source) as unique_sources,
                            AVG(routed_to_count) as avg_routes,
                            SUM(CASE WHEN validated THEN 1 ELSE 0 END) as validated_count
                        FROM intelligence_records
                        GROUP BY day, type
                        WITH NO DATA
                        """
                    )

                    await conn.execute(
                        """
                        SELECT add_continuous_aggregate_policy(
                            'intelligence_daily_stats',
                            start_offset => INTERVAL '3 days',
                            end_offset => INTERVAL '1 day',
                            schedule_interval => INTERVAL '1 day',
                            if_not_exists => TRUE
                        )
                        """
                    )
                    logger.info("✅ Continuous aggregate created (daily stats)")

                else:
                    logger.info("✅ intelligence_records already configured as hypertable")

        except Exception as e:
            logger.warning(f"⚠️  TimescaleDB setup failed: {e}")
            logger.warning("Continuing without TimescaleDB optimization (standard PostgreSQL)")

    # Intelligence Storage

    @retry_with_backoff(
        max_attempts=3, min_wait=1, max_wait=10, exceptions=(asyncpg.PostgresError, Exception)
    )
    async def store_intelligence(
        self,
        intelligence_id: str,
        intelligence_type: str,
        importance: str,
        source: str,
        data: dict[str, Any],
        symbol: str | None = None,
        meta_data: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        validated: bool = False,
        routed_to_count: int = 0,
    ) -> bool:
        """
        Store intelligence record in long-term memory.

        Resilience Features:
        - Bulkhead: Max 20 concurrent write operations
        - Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
        - Health Check: Tracks write reliability

        Args:
            intelligence_id: Unique intelligence ID
            intelligence_type: Type of intelligence
            importance: Importance level
            source: Data source
            data: Intelligence data
            symbol: Optional symbol
            meta_data: Optional metadata
            timestamp: Message timestamp
            validated: Validation status
            routed_to_count: Number of agents routed to

        Returns:
            bool: True if stored successfully
        """
        try:
            async with self.write_bulkhead:
                async with self._session_maker() as session:
                    record = IntelligenceRecord(
                        id=intelligence_id,
                        type=intelligence_type,
                        importance=importance,
                        source=source,
                        symbol=symbol,
                        data=data,
                        meta_data=meta_data or {},
                        timestamp=timestamp or datetime.utcnow(),
                        validated=validated,
                        routed_to_count=routed_to_count,
                        accessed_count=0,
                    )

                    session.add(record)
                    await session.commit()

                    self.health.record_success()

                    logger.debug(
                        "Intelligence stored in LTM", id=intelligence_id, type=intelligence_type
                    )

                    return True

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to store intelligence: {e}", exc_info=True)
            return False

    @retry_with_backoff(
        max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception)
    )
    async def get_intelligence(self, intelligence_id: str) -> dict[str, Any] | None:
        """
        Retrieve intelligence record by ID.

        Resilience Features:
        - Bulkhead: Max 50 concurrent read operations
        - Retry: 3 attempts with exponential backoff (1s, 2s, 4s)

        Args:
            intelligence_id: Intelligence ID

        Returns:
            Optional[Dict]: Intelligence record or None
        """
        try:
            async with self.read_bulkhead:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM intelligence_records
                        WHERE id = $1
                        """,
                        intelligence_id,
                    )

                    if row:
                        # Update access stats
                        await conn.execute(
                            """
                            UPDATE intelligence_records
                            SET accessed_count = accessed_count + 1,
                                last_accessed = $1
                            WHERE id = $2
                            """,
                            datetime.utcnow(),
                            intelligence_id,
                        )

                        self.health.record_success()
                        return dict(row)

                    return None

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to get intelligence: {e}", exc_info=True)
            return None

    @retry_with_backoff(
        max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception)
    )
    async def query_intelligence(
        self,
        intelligence_type: str | None = None,
        symbol: str | None = None,
        importance: str | None = None,
        source: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query intelligence records with filters.

        Resilience Features:
        - Bulkhead: Max 50 concurrent read operations
        - Retry: 3 attempts with exponential backoff (1s, 2s, 4s)

        Args:
            intelligence_type: Filter by type
            symbol: Filter by symbol
            importance: Filter by importance
            source: Filter by source
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum results

        Returns:
            List[Dict]: Matching intelligence records
        """
        try:
            async with self.read_bulkhead:
                conditions = []
                params = []
                param_count = 0

                if intelligence_type:
                    param_count += 1
                    conditions.append(f"type = ${param_count}")
                    params.append(intelligence_type)

                if symbol:
                    param_count += 1
                    conditions.append(f"symbol = ${param_count}")
                    params.append(symbol)

                if importance:
                    param_count += 1
                    conditions.append(f"importance = ${param_count}")
                    params.append(importance)

                if source:
                    param_count += 1
                    conditions.append(f"source = ${param_count}")
                    params.append(source)

                if start_time:
                    param_count += 1
                    conditions.append(f"timestamp >= ${param_count}")
                    params.append(start_time)

                if end_time:
                    param_count += 1
                    conditions.append(f"timestamp <= ${param_count}")
                    params.append(end_time)

                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                param_count += 1
                query = f"""
                    SELECT * FROM intelligence_records
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ${param_count}
                """  # nosec B608 - where_clause built from parameterized conditions, limit is parameterized
                params.append(limit)

                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                    self.health.record_success()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to query intelligence: {e}", exc_info=True)
            return []

    async def get_intelligence_stats(self) -> dict[str, Any]:
        """
        Get statistics about stored intelligence.

        Returns:
            Dict: Intelligence statistics
        """
        try:
            async with self._pool.acquire() as conn:
                # Total intelligence count
                total = await conn.fetchval("SELECT COUNT(*) FROM intelligence_records")

                # Count by type
                by_type = await conn.fetch(
                    "SELECT type, COUNT(*) as count FROM intelligence_records GROUP BY type"
                )

                # Count by importance
                by_importance = await conn.fetch(
                    "SELECT importance, COUNT(*) as count FROM intelligence_records GROUP BY importance"
                )

                # Recent activity
                recent_24h = await conn.fetchval(
                    "SELECT COUNT(*) FROM intelligence_records WHERE timestamp >= NOW() - INTERVAL '24 hours'"
                )

                return {
                    "total_records": total,
                    "by_type": {row["type"]: row["count"] for row in by_type},
                    "by_importance": {row["importance"]: row["count"] for row in by_importance},
                    "last_24_hours": recent_24h,
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {}

    # Agent Storage

    async def store_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: dict[str, Any],
        status: str,
        registered_at: datetime,
        meta_data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store agent registration in long-term memory.

        Args:
            agent_id: Agent ID
            agent_type: Agent type
            capabilities: Agent capabilities
            status: Current status
            registered_at: Registration timestamp
            meta_data: Optional metadata

        Returns:
            bool: True if stored successfully
        """
        try:
            async with self._session_maker() as session:
                record = AgentRecord(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    capabilities=capabilities,
                    status=status,
                    registered_at=registered_at,
                    last_active=registered_at,
                    total_messages_received=0,
                    meta_data=meta_data or {},
                )

                session.add(record)
                await session.commit()

                return True

        except Exception as e:
            logger.error(f"Failed to store agent: {e}", exc_info=True)
            return False

    def is_connected(self) -> bool:
        """Check if PostgreSQL is connected."""
        return self._connected

    async def get_info(self) -> dict[str, Any]:
        """Get PostgreSQL connection information."""
        if not self.is_connected():
            return {"connected": False}

        try:
            async with self._pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size($1))", settings.POSTGRES_DB
                )

                return {
                    "connected": True,
                    "version": version,
                    "database_size": db_size,
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT,
                }

        except Exception as e:
            logger.error(f"Failed to get info: {e}")
            return {"connected": True, "error": str(e)}

    # ========================================================================
    # TIMESCALEDB TIME-SERIES QUERIES
    # ========================================================================

    @retry_with_backoff(
        max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception)
    )
    async def get_time_series_data(
        self,
        symbol: str | None = None,
        intelligence_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        interval: str = "1 hour",
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Get time-bucketed intelligence data using TimescaleDB.

        This leverages TimescaleDB's time_bucket() function for efficient
        time-series aggregation. 100x faster than traditional GROUP BY queries.

        Args:
            symbol: Filter by symbol
            intelligence_type: Filter by type
            start_time: Start of time range
            end_time: End of time range
            interval: Time bucket interval (e.g., '1 hour', '15 minutes', '1 day')
            limit: Maximum number of buckets

        Returns:
            List[Dict]: Time-bucketed data with aggregates
        """
        try:
            async with self.read_bulkhead:
                conditions = []
                params = []
                param_count = 0

                if symbol:
                    param_count += 1
                    conditions.append(f"symbol = ${param_count}")
                    params.append(symbol)

                if intelligence_type:
                    param_count += 1
                    conditions.append(f"type = ${param_count}")
                    params.append(intelligence_type)

                if start_time:
                    param_count += 1
                    conditions.append(f"timestamp >= ${param_count}")
                    params.append(start_time)

                if end_time:
                    param_count += 1
                    conditions.append(f"timestamp <= ${param_count}")
                    params.append(end_time)

                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                param_count += 1
                interval_param = f"${param_count}"
                param_count += 1
                limit_param = f"${param_count}"

                query = f"""
                    SELECT
                        time_bucket({interval_param}, timestamp) AS bucket,
                        type,
                        symbol,
                        COUNT(*) as count,
                        COUNT(DISTINCT source) as unique_sources,
                        AVG(routed_to_count) as avg_routes,
                        MAX(timestamp) as latest_timestamp
                    FROM intelligence_records
                    WHERE {where_clause}
                    GROUP BY bucket, type, symbol
                    ORDER BY bucket DESC
                    LIMIT {limit_param}
                """  # nosec B608 - All parameters are properly escaped and parameterized
                params.extend([interval, limit])

                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                    self.health.record_success()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to get time-series data: {e}", exc_info=True)
            return []

    @retry_with_backoff(
        max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception)
    )
    async def get_hourly_stats(
        self,
        symbol: str | None = None,
        intelligence_type: str | None = None,
        hours_back: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Get pre-computed hourly statistics from continuous aggregate.

        This uses TimescaleDB's continuous aggregates (materialized views)
        that are automatically refreshed. Queries are nearly instantaneous.

        Args:
            symbol: Filter by symbol
            intelligence_type: Filter by type
            hours_back: Number of hours to look back

        Returns:
            List[Dict]: Hourly statistics
        """
        try:
            async with self.read_bulkhead:
                conditions = ["hour >= NOW() - $1::interval"]
                params = [f"{hours_back} hours"]
                param_count = 1

                if symbol:
                    param_count += 1
                    conditions.append(f"symbol = ${param_count}")
                    params.append(symbol)

                if intelligence_type:
                    param_count += 1
                    conditions.append(f"type = ${param_count}")
                    params.append(intelligence_type)

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT
                        hour,
                        type,
                        symbol,
                        message_count,
                        unique_sources,
                        total_routes
                    FROM intelligence_hourly_stats
                    WHERE {where_clause}
                    ORDER BY hour DESC
                """  # nosec B608 - All parameters are properly parameterized

                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                    self.health.record_success()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to get hourly stats: {e}", exc_info=True)
            return []

    @retry_with_backoff(
        max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception)
    )
    async def get_daily_stats(
        self, intelligence_type: str | None = None, days_back: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get pre-computed daily statistics from continuous aggregate.

        Args:
            intelligence_type: Filter by type
            days_back: Number of days to look back

        Returns:
            List[Dict]: Daily statistics
        """
        try:
            async with self.read_bulkhead:
                conditions = ["day >= NOW() - $1::interval"]
                params = [f"{days_back} days"]
                param_count = 1

                if intelligence_type:
                    param_count += 1
                    conditions.append(f"type = ${param_count}")
                    params.append(intelligence_type)

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT
                        day,
                        type,
                        message_count,
                        unique_symbols,
                        unique_sources,
                        avg_routes,
                        validated_count
                    FROM intelligence_daily_stats
                    WHERE {where_clause}
                    ORDER BY day DESC
                """  # nosec B608 - All parameters are properly parameterized

                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                    self.health.record_success()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to get daily stats: {e}", exc_info=True)
            return []

    async def get_compression_stats(self) -> dict[str, Any]:
        """
        Get TimescaleDB compression statistics.

        Shows how much storage is saved through compression.

        Returns:
            Dict: Compression statistics
        """
        try:
            async with self._pool.acquire() as conn:
                # Get compression stats
                compression_stats = await conn.fetch(
                    """
                    SELECT
                        hypertable_name,
                        CASE WHEN before_compression_total_bytes > 0
                            THEN ROUND(100.0 * (before_compression_total_bytes - after_compression_total_bytes) / before_compression_total_bytes, 2)
                            ELSE 0
                        END as compression_ratio,
                        pg_size_pretty(before_compression_total_bytes) as uncompressed_size,
                        pg_size_pretty(after_compression_total_bytes) as compressed_size,
                        pg_size_pretty(before_compression_total_bytes - after_compression_total_bytes) as saved_space
                    FROM timescaledb_information.compression_settings
                    """
                )

                # Get chunk stats
                chunk_stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_chunks,
                        SUM(CASE WHEN is_compressed THEN 1 ELSE 0 END) as compressed_chunks,
                        SUM(CASE WHEN NOT is_compressed THEN 1 ELSE 0 END) as uncompressed_chunks
                    FROM timescaledb_information.chunks
                    WHERE hypertable_name = 'intelligence_records'
                    """
                )

                return {
                    "compression_stats": [dict(row) for row in compression_stats],
                    "chunk_stats": dict(chunk_stats) if chunk_stats else {},
                    "timescaledb_enabled": True,
                }

        except Exception as e:
            logger.error(f"Failed to get compression stats: {e}", exc_info=True)
            return {"timescaledb_enabled": False, "error": str(e)}

    async def get_recent_trends(self, hours: int = 24, limit: int = 10) -> dict[str, Any]:
        """
        Get trending symbols and intelligence types.

        Args:
            hours: Number of hours to analyze
            limit: Number of results per category

        Returns:
            Dict: Trending data
        """
        try:
            async with self._pool.acquire() as conn:
                # Top symbols by message count
                top_symbols = await conn.fetch(
                    """
                    SELECT
                        symbol,
                        COUNT(*) as message_count,
                        COUNT(DISTINCT type) as intelligence_types
                    FROM intelligence_records
                    WHERE timestamp >= NOW() - $1::interval
                        AND symbol IS NOT NULL
                    GROUP BY symbol
                    ORDER BY message_count DESC
                    LIMIT $2
                    """,
                    f"{hours} hours",
                    limit,
                )

                # Top intelligence types
                top_types = await conn.fetch(
                    """
                    SELECT
                        type,
                        COUNT(*) as message_count,
                        COUNT(DISTINCT symbol) as unique_symbols,
                        COUNT(DISTINCT source) as unique_sources
                    FROM intelligence_records
                    WHERE timestamp >= NOW() - $1::interval
                    GROUP BY type
                    ORDER BY message_count DESC
                    LIMIT $2
                    """,
                    f"{hours} hours",
                    limit,
                )

                # Message volume over time (15-minute buckets)
                volume_timeline = await conn.fetch(
                    """
                    SELECT
                        time_bucket('15 minutes', timestamp) AS bucket,
                        COUNT(*) as count
                    FROM intelligence_records
                    WHERE timestamp >= NOW() - $1::interval
                    GROUP BY bucket
                    ORDER BY bucket DESC
                    """,
                    f"{hours} hours",
                )

                return {
                    "period_hours": hours,
                    "top_symbols": [dict(row) for row in top_symbols],
                    "top_types": [dict(row) for row in top_types],
                    "volume_timeline": [dict(row) for row in volume_timeline],
                }

        except Exception as e:
            logger.error(f"Failed to get recent trends: {e}", exc_info=True)
            return {}


# Global PostgreSQL manager instance
_postgres_manager: PostgresManager | None = None


def get_postgres_manager() -> PostgresManager:
    """
    Get the global PostgreSQL manager instance.
    Uses singleton pattern.

    Returns:
        PostgresManager: Global PostgreSQL manager
    """
    global _postgres_manager
    if _postgres_manager is None:
        _postgres_manager = PostgresManager()
    return _postgres_manager
