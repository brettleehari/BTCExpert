"""
CIAL Long-Term Memory (LTM)
PostgreSQL-based persistent intelligence storage with analytics
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api.models.intelligence import IntelligenceMessage
from infrastructure.logging_config import logger
from infrastructure.postgres_manager import get_postgres_manager


class LongTermMemory:
    """
    Long-Term Memory system for CIAL.

    Responsibilities:
    - Persistent intelligence storage (PostgreSQL)
    - Historical data retrieval
    - Analytics and reporting
    - Long-term trend analysis
    - Data archival and lifecycle management
    """

    def __init__(self):
        self.postgres = get_postgres_manager()
        self._archive_threshold_days = 90  # Archive data older than 90 days

    async def store_intelligence(
        self, message: IntelligenceMessage, routed_to_count: int = 0
    ) -> bool:
        """
        Store intelligence message in long-term memory.

        Args:
            message: Intelligence message to store
            routed_to_count: Number of agents message was routed to

        Returns:
            bool: True if stored successfully
        """
        try:
            success = await self.postgres.store_intelligence(
                intelligence_id=message.id,
                intelligence_type=message.type.value,
                importance=message.importance.value,
                source=message.source,
                data=message.data,
                symbol=message.symbol,
                metadata=message.metadata,
                timestamp=message.timestamp,
                validated=message.validated,
                routed_to_count=routed_to_count,
            )

            if success:
                logger.debug(f"Intelligence stored in LTM", id=message.id, type=message.type.value)

            return success

        except Exception as e:
            logger.error(f"Failed to store in LTM: {e}", exc_info=True)
            return False

    async def get_intelligence(self, intelligence_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve intelligence by ID.

        Args:
            intelligence_id: Intelligence ID

        Returns:
            Optional[Dict]: Intelligence record or None
        """
        return await self.postgres.get_intelligence(intelligence_id)

    async def get_historical_prices(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a symbol.

        Args:
            symbol: Cryptocurrency symbol
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum results

        Returns:
            List[Dict]: Historical price records
        """
        return await self.postgres.query_intelligence(
            intelligence_type="price",
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def get_price_trends(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """
        Analyze price trends over a time period.

        Args:
            symbol: Cryptocurrency symbol
            days: Number of days to analyze

        Returns:
            Dict: Trend analysis including avg, min, max, volatility
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        prices = await self.get_historical_prices(symbol=symbol, start_time=start_time, limit=10000)

        if not prices:
            return {}

        price_values = [
            p["data"].get("current_price", 0)
            for p in prices
            if "current_price" in p.get("data", {})
        ]

        if not price_values:
            return {}

        avg_price = sum(price_values) / len(price_values)
        min_price = min(price_values)
        max_price = max(price_values)

        # Calculate volatility (standard deviation)
        variance = sum((p - avg_price) ** 2 for p in price_values) / len(price_values)
        volatility = variance**0.5

        return {
            "symbol": symbol,
            "period_days": days,
            "total_records": len(prices),
            "average_price": avg_price,
            "min_price": min_price,
            "max_price": max_price,
            "volatility": volatility,
            "price_range": max_price - min_price,
            "latest_price": price_values[0] if price_values else 0,
        }

    async def get_sentiment_history(
        self, symbol: Optional[str] = None, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get historical sentiment data.

        Args:
            symbol: Optional symbol filter
            days: Number of days to retrieve

        Returns:
            List[Dict]: Historical sentiment records
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        return await self.postgres.query_intelligence(
            intelligence_type="sentiment", symbol=symbol, start_time=start_time, limit=1000
        )

    async def get_whale_movements(
        self, symbol: Optional[str] = None, min_amount_usd: float = 1000000, days: int = 30  # $1M+
    ) -> List[Dict[str, Any]]:
        """
        Get whale movement history.

        Args:
            symbol: Optional symbol filter
            min_amount_usd: Minimum transaction amount
            days: Number of days to retrieve

        Returns:
            List[Dict]: Whale movement records
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        all_movements = await self.postgres.query_intelligence(
            intelligence_type="whale", symbol=symbol, start_time=start_time, limit=1000
        )

        # Filter by amount
        filtered = [
            m for m in all_movements if m.get("data", {}).get("amount_usd", 0) >= min_amount_usd
        ]

        return filtered

    async def get_critical_events(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent critical intelligence events.

        Args:
            days: Number of days to retrieve
            limit: Maximum results

        Returns:
            List[Dict]: Critical intelligence records
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        return await self.postgres.query_intelligence(
            importance="CRITICAL", start_time=start_time, limit=limit
        )

    async def get_source_analytics(self, source: str) -> Dict[str, Any]:
        """
        Get analytics for a specific data source.

        Args:
            source: Data source identifier

        Returns:
            Dict: Source analytics
        """
        all_records = await self.postgres.query_intelligence(source=source, limit=10000)

        if not all_records:
            return {}

        total = len(all_records)
        by_type = {}
        by_importance = {}

        for record in all_records:
            rec_type = record.get("type", "unknown")
            rec_importance = record.get("importance", "unknown")

            by_type[rec_type] = by_type.get(rec_type, 0) + 1
            by_importance[rec_importance] = by_importance.get(rec_importance, 0) + 1

        return {
            "source": source,
            "total_records": total,
            "by_type": by_type,
            "by_importance": by_importance,
            "oldest_record": all_records[-1].get("timestamp") if all_records else None,
            "newest_record": all_records[0].get("timestamp") if all_records else None,
        }

    async def search_intelligence(
        self, query: str, intelligence_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search intelligence records (full-text search).

        Args:
            query: Search query
            intelligence_type: Optional type filter
            limit: Maximum results

        Returns:
            List[Dict]: Matching intelligence records
        """
        # Simple implementation - can be enhanced with PostgreSQL full-text search
        records = await self.postgres.query_intelligence(
            intelligence_type=intelligence_type, limit=1000
        )

        # Filter by query in data/metadata
        query_lower = query.lower()
        matches = []

        for record in records:
            # Check if query matches in data or metadata
            data_str = str(record.get("data", {})).lower()
            meta_str = str(record.get("metadata", {})).lower()

            if query_lower in data_str or query_lower in meta_str:
                matches.append(record)

            if len(matches) >= limit:
                break

        return matches

    async def get_ltm_stats(self) -> Dict[str, Any]:
        """
        Get Long-Term Memory statistics.

        Returns:
            Dict: LTM statistics
        """
        postgres_stats = await self.postgres.get_intelligence_stats()

        return {
            "storage": "PostgreSQL",
            **postgres_stats,
            "archive_threshold_days": self._archive_threshold_days,
        }

    async def cleanup_old_data(self, days: int = 90) -> int:
        """
        Clean up data older than specified days.

        Args:
            days: Delete data older than this many days

        Returns:
            int: Number of records deleted
        """
        # TODO: Implement archival strategy
        logger.info(f"Cleanup triggered for data older than {days} days")
        return 0


# Global LTM instance
_ltm: Optional[LongTermMemory] = None


def get_long_term_memory() -> LongTermMemory:
    """
    Get the global Long-Term Memory instance.
    Uses singleton pattern.

    Returns:
        LongTermMemory: Global LTM instance
    """
    global _ltm
    if _ltm is None:
        _ltm = LongTermMemory()
    return _ltm
