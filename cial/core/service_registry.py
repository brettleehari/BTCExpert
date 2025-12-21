"""
CIAL Service Registry
Registry for data connectors and external service management
"""

from datetime import datetime
from typing import Dict, List, Optional

from api.models.intelligence import DataConnector, DataConnectorHealth, IntelligenceType
from infrastructure.logging_config import logger


class ServiceRegistry:
    """
    Registry for managing data connector services.

    Responsibilities:
    - Connector registration and discovery
    - Health monitoring
    - Reliability scoring
    - Service availability tracking
    """

    def __init__(self):
        self._connectors: Dict[str, DataConnector] = {}
        self._health_status: Dict[str, DataConnectorHealth] = {}

        logger.info("ServiceRegistry initialized")

    def register_connector(
        self,
        connector_id: str,
        name: str,
        intelligence_types: List[IntelligenceType],
        reliability_score: float = 1.0,
        rate_limit: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> DataConnector:
        """
        Register a data connector.

        Args:
            connector_id: Unique connector identifier
            name: Human-readable connector name
            intelligence_types: Types of intelligence this connector provides
            reliability_score: Initial reliability score (0.0-1.0)
            rate_limit: Rate limit description
            metadata: Additional connector metadata

        Returns:
            DataConnector: Registered connector

        Raises:
            ValueError: If connector_id already exists
        """
        if connector_id in self._connectors:
            raise ValueError(f"Connector {connector_id} is already registered")

        connector = DataConnector(
            connector_id=connector_id,
            name=name,
            intelligence_types=intelligence_types,
            reliability_score=reliability_score,
            rate_limit=rate_limit,
            enabled=True,
            metadata=metadata or {},
        )

        self._connectors[connector_id] = connector

        # Initialize health status
        self._health_status[connector_id] = DataConnectorHealth(
            connector_id=connector_id, healthy=True, success_rate=1.0
        )

        logger.info(
            f"Data connector registered: {connector_id}",
            name=name,
            intelligence_types=[t.value for t in intelligence_types],
        )

        return connector

    def unregister_connector(self, connector_id: str) -> bool:
        """
        Unregister a data connector.

        Args:
            connector_id: Connector identifier

        Returns:
            bool: True if unregistered, False if not found
        """
        if connector_id not in self._connectors:
            return False

        del self._connectors[connector_id]
        if connector_id in self._health_status:
            del self._health_status[connector_id]

        logger.info(f"Data connector unregistered: {connector_id}")

        return True

    def get_connector(self, connector_id: str) -> Optional[DataConnector]:
        """Get connector by ID."""
        return self._connectors.get(connector_id)

    def get_all_connectors(self) -> List[DataConnector]:
        """Get all registered connectors."""
        return list(self._connectors.values())

    def get_enabled_connectors(self) -> List[DataConnector]:
        """Get only enabled connectors."""
        return [c for c in self._connectors.values() if c.enabled]

    def get_connectors_by_type(self, intelligence_type: IntelligenceType) -> List[DataConnector]:
        """
        Get connectors that provide specific intelligence type.

        Args:
            intelligence_type: Intelligence type to filter by

        Returns:
            List[DataConnector]: Matching connectors
        """
        return [
            conn
            for conn in self._connectors.values()
            if intelligence_type in conn.intelligence_types and conn.enabled
        ]

    def enable_connector(self, connector_id: str) -> bool:
        """Enable a connector."""
        connector = self._connectors.get(connector_id)
        if not connector:
            return False

        connector.enabled = True
        logger.info(f"Connector enabled: {connector_id}")
        return True

    def disable_connector(self, connector_id: str) -> bool:
        """Disable a connector."""
        connector = self._connectors.get(connector_id)
        if not connector:
            return False

        connector.enabled = False
        logger.info(f"Connector disabled: {connector_id}")
        return True

    # Health Monitoring

    def report_success(self, connector_id: str):
        """Report successful connector operation."""
        if connector_id not in self._health_status:
            return

        health = self._health_status[connector_id]
        health.request_count += 1
        health.last_success = datetime.utcnow()
        health.healthy = True

        # Update success rate (exponential moving average)
        alpha = 0.1
        health.success_rate = (1 - alpha) * health.success_rate + alpha * 1.0

        # Update connector reliability score
        if connector_id in self._connectors:
            self._connectors[connector_id].reliability_score = health.success_rate

    def report_error(self, connector_id: str, error_message: str):
        """Report connector error."""
        if connector_id not in self._health_status:
            return

        health = self._health_status[connector_id]
        health.request_count += 1
        health.error_count += 1
        health.last_error = error_message

        # Update success rate
        alpha = 0.1
        health.success_rate = (1 - alpha) * health.success_rate + alpha * 0.0

        # Mark as unhealthy if success rate drops below 50%
        if health.success_rate < 0.5:
            health.healthy = False
            logger.warning(
                f"Connector unhealthy: {connector_id}",
                success_rate=health.success_rate,
                error_count=health.error_count,
            )

        # Update connector reliability score
        if connector_id in self._connectors:
            self._connectors[connector_id].reliability_score = health.success_rate

    def get_health_status(self, connector_id: str) -> Optional[DataConnectorHealth]:
        """Get health status for a connector."""
        return self._health_status.get(connector_id)

    def get_all_health_statuses(self) -> List[DataConnectorHealth]:
        """Get health status for all connectors."""
        return list(self._health_status.values())

    def get_unhealthy_connectors(self) -> List[str]:
        """Get list of unhealthy connector IDs."""
        return [
            connector_id
            for connector_id, health in self._health_status.items()
            if not health.healthy
        ]

    def get_registry_stats(self) -> Dict:
        """
        Get registry statistics.

        Returns:
            Dict: Registry statistics
        """
        total_connectors = len(self._connectors)
        enabled_connectors = len(self.get_enabled_connectors())
        healthy_connectors = sum(1 for h in self._health_status.values() if h.healthy)

        total_requests = sum(h.request_count for h in self._health_status.values())
        total_errors = sum(h.error_count for h in self._health_status.values())

        return {
            "total_connectors": total_connectors,
            "enabled_connectors": enabled_connectors,
            "healthy_connectors": healthy_connectors,
            "unhealthy_connectors": total_connectors - healthy_connectors,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "overall_success_rate": (
                (total_requests - total_errors) / total_requests if total_requests > 0 else 1.0
            ),
        }


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """
    Get the global service registry instance.
    Uses singleton pattern.

    Returns:
        ServiceRegistry: Global registry instance
    """
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


# Initialize default connectors
def initialize_default_connectors():
    """Initialize default data connector configurations."""
    registry = get_service_registry()

    # Only register if not already registered
    if not registry.get_connector("coingecko"):
        # CoinGecko
        registry.register_connector(
            connector_id="coingecko",
            name="CoinGecko Price API",
            intelligence_types=[IntelligenceType.PRICE],
            rate_limit="50/minute",
            metadata={"website": "https://coingecko.com", "version": "v3"},
        )

        # NewsAPI
        registry.register_connector(
            connector_id="newsapi",
            name="NewsAPI",
            intelligence_types=[IntelligenceType.SENTIMENT],
            rate_limit="1000/day",
            metadata={"website": "https://newsapi.org"},
        )

        # Etherscan
        registry.register_connector(
            connector_id="etherscan",
            name="Etherscan",
            intelligence_types=[IntelligenceType.ONCHAIN, IntelligenceType.WHALE],
            rate_limit="5/second",
            metadata={"website": "https://etherscan.io"},
        )

        logger.info("Default data connectors initialized")
