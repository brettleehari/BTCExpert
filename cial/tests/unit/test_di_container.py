"""
Tests for Dependency Injection Container
Demonstrates how DI makes testing easier with mock providers
"""

from unittest.mock import AsyncMock, Mock

import pytest
from dependency_injector import providers

from infrastructure.container import get_container, reset_container


class TestDIContainer:
    """Test suite for DI container functionality."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def test_container_singleton(self):
        """Test that container is a singleton."""
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2

    def test_redis_manager_singleton(self):
        """Test that Redis Manager is singleton."""
        container = get_container()
        redis1 = container.redis_manager()
        redis2 = container.redis_manager()
        assert redis1 is redis2

    def test_postgres_manager_singleton(self):
        """Test that PostgreSQL Manager is singleton."""
        container = get_container()
        postgres1 = container.postgres_manager()
        postgres2 = container.postgres_manager()
        assert postgres1 is postgres2

    def test_intelligence_broker_singleton(self):
        """Test that Intelligence Broker is singleton."""
        container = get_container()
        broker1 = container.intelligence_broker()
        broker2 = container.intelligence_broker()
        assert broker1 is broker2

    def test_mock_redis_manager(self):
        """Test mocking Redis Manager for testing."""
        container = get_container()

        # Create mock Redis Manager
        mock_redis = Mock()
        mock_redis.is_connected.return_value = True
        mock_redis.get.return_value = "test_value"

        # Override provider with mock
        container.redis_manager.override(providers.Singleton(lambda: mock_redis))

        # Get manager and verify it's the mock
        redis = container.redis_manager()
        assert redis is mock_redis
        assert redis.is_connected() is True
        assert redis.get("test_key") == "test_value"

        # Reset override
        container.redis_manager.reset_override()

    @pytest.mark.asyncio
    async def test_mock_postgres_manager(self):
        """Test mocking PostgreSQL Manager for testing."""
        container = get_container()

        # Create mock PostgreSQL Manager
        mock_postgres = AsyncMock()
        mock_postgres.is_connected.return_value = True
        mock_postgres.store_intelligence = AsyncMock(return_value=True)

        # Override provider with mock
        container.postgres_manager.override(providers.Singleton(lambda: mock_postgres))

        # Get manager and verify it's the mock
        postgres = container.postgres_manager()
        assert postgres is mock_postgres
        assert postgres.is_connected() is True

        # Test async method
        result = await postgres.store_intelligence(
            intelligence_id="test_id",
            intelligence_type="price",
            importance="high",
            source="test",
            data={"price": 50000},
        )
        assert result is True
        mock_postgres.store_intelligence.assert_called_once()

        # Reset override
        container.postgres_manager.reset_override()

    def test_mock_intelligence_broker(self):
        """Test mocking Intelligence Broker for testing."""
        container = get_container()

        # Create mock Intelligence Broker
        mock_broker = Mock()
        mock_message = Mock()
        mock_message.id = "test_msg_id"
        mock_broker.process_intelligence.return_value = mock_message

        # Override provider with mock
        container.intelligence_broker.override(providers.Singleton(lambda: mock_broker))

        # Get broker and verify it's the mock
        broker = container.intelligence_broker()
        assert broker is mock_broker

        # Test processing
        from api.models.intelligence import IntelligenceType

        message = broker.process_intelligence(
            intelligence_type=IntelligenceType.PRICE, source="test", data={"price": 50000}
        )
        assert message.id == "test_msg_id"
        mock_broker.process_intelligence.assert_called_once()

        # Reset override
        container.intelligence_broker.reset_override()

    def test_container_reset(self):
        """Test that container reset works."""
        container1 = get_container()
        reset_container()
        container2 = get_container()
        assert container1 is not container2


class TestDIDependencyGraph:
    """Test dependency resolution and injection."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def test_short_term_memory_receives_redis(self):
        """Test that STM gets Redis Manager injected."""
        container = get_container()
        stm = container.short_term_memory()
        # STM should have redis_manager attribute injected
        assert hasattr(stm, "redis")

    def test_long_term_memory_receives_postgres(self):
        """Test that LTM gets PostgreSQL Manager injected."""
        container = get_container()
        ltm = container.long_term_memory()
        # LTM should have postgres_manager attribute injected
        assert hasattr(ltm, "postgres")


class TestBackwardCompatibility:
    """Test backward compatibility helpers."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def test_backward_compatible_helpers(self):
        """Test that backward-compatible get_* functions work."""
        from infrastructure.container import (
            get_agent_registry,
            get_intelligence_broker,
            get_postgres_manager,
            get_redis_manager,
        )

        # Test helpers return singleton instances
        redis1 = get_redis_manager()
        redis2 = get_redis_manager()
        assert redis1 is redis2

        postgres1 = get_postgres_manager()
        postgres2 = get_postgres_manager()
        assert postgres1 is postgres2

        broker1 = get_intelligence_broker()
        broker2 = get_intelligence_broker()
        assert broker1 is broker2

        registry1 = get_agent_registry()
        registry2 = get_agent_registry()
        assert registry1 is registry2


# ============================================================================
# EXAMPLE: How to use DI in tests
# ============================================================================


@pytest.fixture
def mock_container():
    """
    Fixture that provides a container with mocked dependencies.

    Use this in tests to avoid hitting real infrastructure.

    Example:
        def test_my_feature(mock_container):
            broker = mock_container.intelligence_broker()
            # broker is mocked, no real Redis/Kafka/PostgreSQL needed
    """
    reset_container()
    container = get_container()

    # Mock Redis
    mock_redis = Mock()
    mock_redis.is_connected.return_value = True
    container.redis_manager.override(providers.Singleton(lambda: mock_redis))

    # Mock Kafka
    mock_kafka = Mock()
    mock_kafka.is_connected.return_value = True
    container.kafka_manager.override(providers.Singleton(lambda: mock_kafka))

    # Mock PostgreSQL
    mock_postgres = AsyncMock()
    mock_postgres.is_connected.return_value = True
    container.postgres_manager.override(providers.Singleton(lambda: mock_postgres))

    yield container

    # Cleanup
    container.redis_manager.reset_override()
    container.kafka_manager.reset_override()
    container.postgres_manager.reset_override()


def test_example_with_mock_container(mock_container):
    """Example test using mocked container."""
    # Get Intelligence Broker (will use mocked dependencies)
    broker = mock_container.intelligence_broker()

    # Broker is real, but Redis/Kafka/PostgreSQL are mocked
    # This allows testing broker logic without infrastructure
    assert broker is not None

    # Get mocked Redis (verify it's mocked)
    redis = mock_container.redis_manager()
    assert redis.is_connected() is True
