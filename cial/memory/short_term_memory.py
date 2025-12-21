"""
CIAL Short-Term Memory (STM)
Redis-based real-time intelligence cache with TTL-based lifecycle
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api.models.intelligence import IntelligenceMessage, IntelligenceType
from infrastructure.config import settings
from infrastructure.logging_config import logger
from infrastructure.redis_manager import get_redis_manager


class ShortTermMemory:
    """
    Short-Term Memory system for CIAL.

    Responsibilities:
    - Cache hot intelligence data (1-24 hour retention)
    - Agent context storage and retrieval
    - Real-time market state
    - TTL-based automatic cleanup
    """

    def __init__(self):
        self.redis = get_redis_manager()
        self._key_prefix = "cial:stm:"

    def _make_key(self, *parts: str) -> str:
        """Create Redis key with prefix."""
        return self._key_prefix + ":".join(parts)

    # Intelligence Caching

    def cache_intelligence(self, message: IntelligenceMessage, ttl: int | None = None) -> bool:
        """
        Cache intelligence message in STM.

        Args:
            message: Intelligence message to cache
            ttl: Time-to-live in seconds (uses type-specific default if None)

        Returns:
            bool: True if cached successfully
        """
        try:
            # Determine TTL based on intelligence type
            if ttl is None:
                ttl = self._get_ttl_for_type(message.type)

            # Create key: intelligence:{type}:{symbol}:{id}
            key = self._make_key(
                "intelligence", message.type.value, message.symbol or "global", message.id
            )

            # Serialize message
            data = message.model_dump_json()

            # Store with TTL
            self.redis.client.setex(key, ttl, data)

            # Add to type-specific sorted set (score = timestamp)
            list_key = self._make_key("list", message.type.value, message.symbol or "global")
            score = message.timestamp.timestamp()
            self.redis.client.zadd(list_key, {message.id: score})
            self.redis.client.expire(list_key, ttl)

            logger.debug(
                f"Intelligence cached: {message.id}",
                type=message.type.value,
                symbol=message.symbol,
                ttl=ttl,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to cache intelligence: {e}", exc_info=True)
            return False

    def get_intelligence(
        self, message_id: str, intelligence_type: IntelligenceType, symbol: str | None = None
    ) -> IntelligenceMessage | None:
        """
        Retrieve cached intelligence message.

        Args:
            message_id: Intelligence message ID
            intelligence_type: Type of intelligence
            symbol: Cryptocurrency symbol (optional)

        Returns:
            Optional[IntelligenceMessage]: Cached message or None
        """
        try:
            key = self._make_key(
                "intelligence", intelligence_type.value, symbol or "global", message_id
            )

            data = self.redis.client.get(key)
            if data:
                return IntelligenceMessage.model_validate_json(data)

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve intelligence: {e}", exc_info=True)
            return None

    def get_recent_intelligence(
        self, intelligence_type: IntelligenceType, symbol: str | None = None, limit: int = 100
    ) -> list[IntelligenceMessage]:
        """
        Get recent intelligence messages from cache.

        Args:
            intelligence_type: Type of intelligence
            symbol: Filter by symbol (optional)
            limit: Maximum number of messages

        Returns:
            List[IntelligenceMessage]: Recent messages (newest first)
        """
        try:
            list_key = self._make_key("list", intelligence_type.value, symbol or "global")

            # Get most recent message IDs from sorted set (highest scores first)
            message_ids = self.redis.client.zrevrange(list_key, 0, limit - 1)

            messages = []
            for msg_id in message_ids:
                msg = self.get_intelligence(msg_id, intelligence_type, symbol)
                if msg:
                    messages.append(msg)

            return messages

        except Exception as e:
            logger.error(f"Failed to get recent intelligence: {e}", exc_info=True)
            return []

    def get_current_price(self, symbol: str) -> dict[str, Any] | None:
        """
        Get current cached price for a symbol.

        Args:
            symbol: Cryptocurrency symbol

        Returns:
            Optional[Dict]: Price data or None
        """
        messages = self.get_recent_intelligence(
            intelligence_type=IntelligenceType.PRICE, symbol=symbol, limit=1
        )

        if messages:
            return messages[0].data

        return None

    # Agent Context Management

    def store_agent_context(
        self, agent_id: str, context: dict[str, Any], ttl: int = 86400  # 24 hours default
    ) -> bool:
        """
        Store agent's working context.

        Args:
            agent_id: Agent identifier
            context: Context data to store
            ttl: Time-to-live in seconds

        Returns:
            bool: True if stored successfully
        """
        try:
            key = self._make_key("agent_context", agent_id)
            data = json.dumps(context)
            self.redis.client.setex(key, ttl, data)

            logger.debug(f"Agent context stored: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store agent context: {e}", exc_info=True)
            return False

    def get_agent_context(self, agent_id: str) -> dict[str, Any] | None:
        """
        Retrieve agent's working context.

        Args:
            agent_id: Agent identifier

        Returns:
            Optional[Dict]: Agent context or None
        """
        try:
            key = self._make_key("agent_context", agent_id)
            data = self.redis.client.get(key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Failed to get agent context: {e}", exc_info=True)
            return None

    def store_agent_decision(
        self, agent_id: str, decision: dict[str, Any], ttl: int = 86400
    ) -> bool:
        """
        Store agent decision in STM.

        Args:
            agent_id: Agent identifier
            decision: Decision data
            ttl: Time-to-live in seconds

        Returns:
            bool: True if stored successfully
        """
        try:
            # Store individual decision
            decision_id = decision.get("id", datetime.utcnow().isoformat())
            key = self._make_key("agent_decision", agent_id, decision_id)
            data = json.dumps(decision)
            self.redis.client.setex(key, ttl, data)

            # Add to agent's decision list
            list_key = self._make_key("agent_decisions", agent_id)
            score = datetime.utcnow().timestamp()
            self.redis.client.zadd(list_key, {decision_id: score})
            self.redis.client.expire(list_key, ttl)

            logger.debug(f"Agent decision stored: {agent_id}/{decision_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store agent decision: {e}", exc_info=True)
            return False

    def get_agent_decisions(self, agent_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent agent decisions.

        Args:
            agent_id: Agent identifier
            limit: Maximum number of decisions

        Returns:
            List[Dict]: Recent decisions (newest first)
        """
        try:
            list_key = self._make_key("agent_decisions", agent_id)
            decision_ids = self.redis.client.zrevrange(list_key, 0, limit - 1)

            decisions = []
            for decision_id in decision_ids:
                key = self._make_key("agent_decision", agent_id, decision_id)
                data = self.redis.client.get(key)
                if data:
                    decisions.append(json.loads(data))

            return decisions

        except Exception as e:
            logger.error(f"Failed to get agent decisions: {e}", exc_info=True)
            return []

    # Market State

    def store_market_state(self, state: dict[str, Any], ttl: int = 3600) -> bool:  # 1 hour
        """
        Store current market state.

        Args:
            state: Market state data
            ttl: Time-to-live in seconds

        Returns:
            bool: True if stored successfully
        """
        try:
            key = self._make_key("market_state")
            data = json.dumps(state)
            self.redis.client.setex(key, ttl, data)

            logger.debug("Market state updated")
            return True

        except Exception as e:
            logger.error(f"Failed to store market state: {e}", exc_info=True)
            return False

    def get_market_state(self) -> dict[str, Any] | None:
        """
        Get current market state.

        Returns:
            Optional[Dict]: Market state or None
        """
        try:
            key = self._make_key("market_state")
            data = self.redis.client.get(key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Failed to get market state: {e}", exc_info=True)
            return None

    # Utility Methods

    def _get_ttl_for_type(self, intelligence_type: IntelligenceType) -> int:
        """Get TTL based on intelligence type."""
        ttl_map = {
            IntelligenceType.PRICE: settings.TTL_LIVE_PRICES,
            IntelligenceType.SENTIMENT: settings.TTL_SENTIMENT,
            IntelligenceType.WHALE: settings.TTL_WHALE_MOVEMENTS,
            IntelligenceType.TECHNICAL: settings.TTL_TECHNICAL_INDICATORS,
            IntelligenceType.ONCHAIN: settings.TTL_WHALE_MOVEMENTS,
            IntelligenceType.REGULATORY: settings.TTL_BREAKING_NEWS,
            IntelligenceType.DEFI: settings.TTL_BREAKING_NEWS,
        }

        return ttl_map.get(intelligence_type, settings.TTL_LIVE_PRICES)

    def clear_agent_data(self, agent_id: str) -> bool:
        """
        Clear all data for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            bool: True if cleared successfully
        """
        try:
            # Delete agent context
            context_key = self._make_key("agent_context", agent_id)
            self.redis.client.delete(context_key)

            # Delete agent decisions list
            decisions_key = self._make_key("agent_decisions", agent_id)
            self.redis.client.delete(decisions_key)

            logger.info(f"Agent data cleared: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear agent data: {e}", exc_info=True)
            return False

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get STM cache statistics.

        Returns:
            Dict: Cache statistics
        """
        try:
            pattern = self._key_prefix + "*"
            keys = list(self.redis.client.scan_iter(pattern))

            # Count by type
            intelligence_keys = [k for k in keys if ":intelligence:" in k]
            context_keys = [k for k in keys if ":agent_context:" in k]
            decision_keys = [k for k in keys if ":agent_decision:" in k]

            return {
                "total_keys": len(keys),
                "intelligence_cached": len(intelligence_keys),
                "agent_contexts": len(context_keys),
                "agent_decisions": len(decision_keys),
                "redis_info": self.redis.get_info(),
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}", exc_info=True)
            return {}


# Global STM instance
_stm: ShortTermMemory | None = None


def get_short_term_memory() -> ShortTermMemory:
    """
    Get the global Short-Term Memory instance.
    Uses singleton pattern.

    Returns:
        ShortTermMemory: Global STM instance
    """
    global _stm
    if _stm is None:
        _stm = ShortTermMemory()
    return _stm
