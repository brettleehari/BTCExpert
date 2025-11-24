"""
CIAL Intelligence Broker
Central intelligence routing and service discovery for crypto agents
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from collections import defaultdict

from api.models.intelligence import (
    IntelligenceMessage, IntelligenceImportance, IntelligenceType,
    Agent, DataConnector
)
from core.agent_registry import get_agent_registry
from infrastructure.logging_config import logger, log_intelligence_event
from memory.short_term_memory import get_short_term_memory


class IntelligenceBroker:
    """
    Central intelligence broker for CIAL.

    Responsibilities:
    - Intelligence message classification
    - Routing intelligence to interested agents
    - Data normalization and validation
    - Cross-source intelligence fusion
    - Service discovery for data connectors
    """

    def __init__(self):
        self.agent_registry = get_agent_registry()
        self.stm = get_short_term_memory()
        self._connectors: Dict[str, DataConnector] = {}
        self._message_history: List[IntelligenceMessage] = []
        self._routing_stats = defaultdict(int)

        logger.info("IntelligenceBroker initialized")

    # Intelligence Processing

    def process_intelligence(
        self,
        intelligence_type: IntelligenceType,
        source: str,
        data: Dict[str, Any],
        symbol: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IntelligenceMessage:
        """
        Process raw intelligence data through the CIAL pipeline.

        Pipeline: RAW DATA → VALIDATION → ENRICHMENT → CLASSIFICATION → ROUTING

        Args:
            intelligence_type: Type of intelligence
            source: Data source identifier
            data: Intelligence data payload
            symbol: Optional cryptocurrency symbol
            metadata: Optional metadata

        Returns:
            IntelligenceMessage: Processed intelligence message
        """
        # 1. Create intelligence message
        message = self._create_message(
            intelligence_type=intelligence_type,
            source=source,
            data=data,
            symbol=symbol,
            metadata=metadata or {}
        )

        # 2. Validate (placeholder for now)
        validated = self._validate_intelligence(message)
        message.validated = validated

        # 3. Enrich with cross-source data (placeholder)
        enriched_message = self._enrich_intelligence(message)

        # 4. Classify importance
        classified_message = self._classify_importance(enriched_message)

        # 5. Cache in Short-Term Memory
        self.stm.cache_intelligence(classified_message)

        # 6. Route to interested agents
        routed_count = self._route_to_agents(classified_message)

        # 7. Store in history (limited size)
        self._store_message(classified_message)

        # 7. Log intelligence event
        log_intelligence_event(
            event_type=classified_message.type.value,
            source=source,
            importance=classified_message.importance.value,
            symbol=symbol,
            routed_to=routed_count
        )

        logger.info(
            f"Intelligence processed: {classified_message.id}",
            type=classified_message.type.value,
            importance=classified_message.importance.value,
            routed_to=routed_count
        )

        return classified_message

    def _create_message(
        self,
        intelligence_type: IntelligenceType,
        source: str,
        data: Dict[str, Any],
        symbol: Optional[str],
        metadata: Dict[str, Any]
    ) -> IntelligenceMessage:
        """Create intelligence message with unique ID and timestamp."""
        message_id = f"{intelligence_type.value}_{symbol or 'global'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        return IntelligenceMessage(
            id=message_id,
            type=intelligence_type,
            importance=IntelligenceImportance.NORMAL,  # Will be classified later
            source=source,
            symbol=symbol,
            data=data,
            metadata=metadata,
            timestamp=datetime.utcnow(),
            validated=False
        )

    def _validate_intelligence(self, message: IntelligenceMessage) -> bool:
        """
        Validate intelligence data.
        TODO: Implement cross-source validation in Session 8
        """
        # Basic validation: check required fields
        if not message.data:
            return False

        # Check if source is registered
        if message.source not in self._connectors:
            logger.warning(f"Intelligence from unregistered source: {message.source}")

        return True

    def _enrich_intelligence(self, message: IntelligenceMessage) -> IntelligenceMessage:
        """
        Enrich intelligence with additional context.
        TODO: Implement cross-source enrichment in Session 5+
        """
        # Placeholder: Add source reliability if connector is registered
        if message.source in self._connectors:
            connector = self._connectors[message.source]
            message.metadata["source_reliability"] = connector.reliability_score

        return message

    def _classify_importance(self, message: IntelligenceMessage) -> IntelligenceMessage:
        """
        Classify intelligence importance based on type and data.

        Classification Rules:
        - CRITICAL: Major price movements (>5%), whale movements (>$10M), breaking news
        - NORMAL: Regular updates, moderate changes
        - LOW: Minor updates, informational data
        """
        importance = IntelligenceImportance.NORMAL

        if message.type == IntelligenceType.PRICE:
            # Price intelligence
            price_change = message.data.get("price_change_percentage_24h", 0)
            if abs(price_change) > 5.0:
                importance = IntelligenceImportance.CRITICAL
            elif abs(price_change) < 1.0:
                importance = IntelligenceImportance.LOW

        elif message.type == IntelligenceType.WHALE:
            # Whale movement intelligence
            amount = message.data.get("amount_usd", 0)
            if amount > 10_000_000:  # $10M+
                importance = IntelligenceImportance.CRITICAL
            elif amount > 1_000_000:  # $1M+
                importance = IntelligenceImportance.NORMAL
            else:
                importance = IntelligenceImportance.LOW

        elif message.type == IntelligenceType.SENTIMENT:
            # Sentiment intelligence
            confidence = message.data.get("confidence", 0)
            sentiment_score = message.data.get("sentiment_score", 0)
            if confidence > 0.8 and abs(sentiment_score) > 0.5:
                importance = IntelligenceImportance.CRITICAL
            elif confidence > 0.5:
                importance = IntelligenceImportance.NORMAL
            else:
                importance = IntelligenceImportance.LOW

        elif message.type in [IntelligenceType.REGULATORY, IntelligenceType.DEFI]:
            # Regulatory and DeFi events are generally important
            importance = IntelligenceImportance.CRITICAL

        message.importance = importance
        return message

    def _route_to_agents(self, message: IntelligenceMessage) -> int:
        """
        Route intelligence message to interested agents.

        Args:
            message: Intelligence message to route

        Returns:
            int: Number of agents the message was routed to
        """
        # Find agents interested in this intelligence
        interested_agents = self.agent_registry.get_agents_for_intelligence(
            intelligence_type=message.type,
            symbol=message.symbol
        )

        # Filter by minimum importance level
        eligible_agents = [
            agent for agent in interested_agents
            if self._meets_importance_threshold(message.importance, agent.capabilities.min_importance)
        ]

        # Update routing stats
        self._routing_stats[message.type.value] += len(eligible_agents)

        # TODO: Actual routing will be implemented with Kafka in Session 4
        # For now, just update agent activity
        for agent in eligible_agents:
            self.agent_registry.update_agent_activity(agent.agent_id)

        return len(eligible_agents)

    def _meets_importance_threshold(
        self,
        message_importance: IntelligenceImportance,
        min_importance: IntelligenceImportance
    ) -> bool:
        """Check if message importance meets agent's minimum threshold."""
        importance_order = {
            IntelligenceImportance.LOW: 0,
            IntelligenceImportance.NORMAL: 1,
            IntelligenceImportance.CRITICAL: 2
        }

        return importance_order[message_importance] >= importance_order[min_importance]

    def _store_message(self, message: IntelligenceMessage):
        """
        Store message in limited history.
        TODO: Move to STM (Session 3) and LTM (Session 6)
        """
        self._message_history.append(message)

        # Keep only last 1000 messages in memory
        if len(self._message_history) > 1000:
            self._message_history = self._message_history[-1000:]

    # Data Connector Management

    def register_connector(self, connector: DataConnector) -> bool:
        """
        Register a data connector with the broker.

        Args:
            connector: Data connector to register

        Returns:
            bool: True if registered, False if already exists
        """
        if connector.connector_id in self._connectors:
            logger.warning(f"Connector already registered: {connector.connector_id}")
            return False

        self._connectors[connector.connector_id] = connector

        logger.info(
            f"Data connector registered: {connector.connector_id}",
            intelligence_types=connector.intelligence_types
        )

        return True

    def get_connector(self, connector_id: str) -> Optional[DataConnector]:
        """Get data connector by ID."""
        return self._connectors.get(connector_id)

    def get_all_connectors(self) -> List[DataConnector]:
        """Get all registered data connectors."""
        return list(self._connectors.values())

    def get_connectors_by_type(self, intelligence_type: IntelligenceType) -> List[DataConnector]:
        """Get connectors that provide specific intelligence type."""
        return [
            conn for conn in self._connectors.values()
            if intelligence_type in conn.intelligence_types and conn.enabled
        ]

    # Query Methods

    def get_recent_intelligence(
        self,
        intelligence_type: Optional[IntelligenceType] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[IntelligenceMessage]:
        """
        Get recent intelligence messages.

        Args:
            intelligence_type: Optional filter by type
            symbol: Optional filter by symbol
            limit: Maximum number of messages to return

        Returns:
            List[IntelligenceMessage]: Recent intelligence messages
        """
        messages = self._message_history

        # Apply filters
        if intelligence_type:
            messages = [m for m in messages if m.type == intelligence_type]

        if symbol:
            messages = [m for m in messages if m.symbol == symbol]

        # Return most recent first, limited
        return sorted(messages, key=lambda m: m.timestamp, reverse=True)[:limit]

    def get_broker_stats(self) -> Dict[str, Any]:
        """
        Get broker statistics.

        Returns:
            Dict: Broker statistics
        """
        return {
            "total_messages_processed": len(self._message_history),
            "registered_connectors": len(self._connectors),
            "active_connectors": sum(1 for c in self._connectors.values() if c.enabled),
            "routing_stats": dict(self._routing_stats),
            "agent_stats": self.agent_registry.get_registry_stats()
        }


# Global broker instance
_broker: Optional[IntelligenceBroker] = None


def get_intelligence_broker() -> IntelligenceBroker:
    """
    Get the global intelligence broker instance.
    Uses singleton pattern.

    Returns:
        IntelligenceBroker: Global broker instance
    """
    global _broker
    if _broker is None:
        _broker = IntelligenceBroker()
    return _broker
