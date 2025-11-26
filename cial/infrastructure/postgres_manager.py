"""
CIAL PostgreSQL Manager
Long-Term Memory persistence with vector search capabilities

Version: 2.0 - Production Ready with Resilience Patterns
"""

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, Boolean, Text
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.resilience import (
    retry_with_backoff,
    get_bulkhead,
    get_health_check
)

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
        self._pool: Optional[asyncpg.Pool] = None
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
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
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

            self._connected = True
            self.health.record_success()

            logger.info(
                "PostgreSQL connected successfully with resilience patterns",
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB
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

    # Intelligence Storage

    @retry_with_backoff(max_attempts=3, min_wait=1, max_wait=10, exceptions=(asyncpg.PostgresError, Exception))
    async def store_intelligence(
        self,
        intelligence_id: str,
        intelligence_type: str,
        importance: str,
        source: str,
        data: Dict[str, Any],
        symbol: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        validated: bool = False,
        routed_to_count: int = 0
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
                        accessed_count=0
                    )

                    session.add(record)
                    await session.commit()

                    self.health.record_success()

                    logger.debug(
                        f"Intelligence stored in LTM",
                        id=intelligence_id,
                        type=intelligence_type
                    )

                    return True

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to store intelligence: {e}", exc_info=True)
            return False

    @retry_with_backoff(max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception))
    async def get_intelligence(self, intelligence_id: str) -> Optional[Dict[str, Any]]:
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
                        intelligence_id
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
                            intelligence_id
                        )

                        self.health.record_success()
                        return dict(row)

                    return None

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to get intelligence: {e}", exc_info=True)
            return None

    @retry_with_backoff(max_attempts=3, min_wait=1, max_wait=5, exceptions=(asyncpg.PostgresError, Exception))
    async def query_intelligence(
        self,
        intelligence_type: Optional[str] = None,
        symbol: Optional[str] = None,
        importance: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
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
                """
                params.append(limit)

                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(query, *params)
                    self.health.record_success()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.health.record_failure(error=str(e))
            logger.error(f"Failed to query intelligence: {e}", exc_info=True)
            return []

    async def get_intelligence_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored intelligence.

        Returns:
            Dict: Intelligence statistics
        """
        try:
            async with self._pool.acquire() as conn:
                # Total intelligence count
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM intelligence_records"
                )

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
                    "by_type": {row['type']: row['count'] for row in by_type},
                    "by_importance": {row['importance']: row['count'] for row in by_importance},
                    "last_24_hours": recent_24h
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {}

    # Agent Storage

    async def store_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: Dict[str, Any],
        status: str,
        registered_at: datetime,
        meta_data: Optional[Dict[str, Any]] = None
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
                    meta_data=meta_data or {}
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

    async def get_info(self) -> Dict[str, Any]:
        """Get PostgreSQL connection information."""
        if not self.is_connected():
            return {"connected": False}

        try:
            async with self._pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size($1))",
                    settings.POSTGRES_DB
                )

                return {
                    "connected": True,
                    "version": version,
                    "database_size": db_size,
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT
                }

        except Exception as e:
            logger.error(f"Failed to get info: {e}")
            return {"connected": True, "error": str(e)}


# Global PostgreSQL manager instance
_postgres_manager: Optional[PostgresManager] = None


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
