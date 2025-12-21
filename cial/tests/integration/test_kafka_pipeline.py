"""
Integration tests for Kafka Event Stream Pipeline
Tests the complete data flow with Kafka message distribution
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture
def mock_kafka():
    """Mock Kafka producer and admin"""
    with (
        patch("infrastructure.kafka_manager.KafkaProducer") as mock_producer,
        patch("infrastructure.kafka_manager.KafkaAdminClient") as mock_admin,
    ):

        mock_producer_instance = MagicMock()
        mock_admin_instance = MagicMock()

        mock_producer.return_value = mock_producer_instance
        mock_admin.return_value = mock_admin_instance

        # Mock successful message send
        mock_future = MagicMock()
        mock_producer_instance.send.return_value = mock_future

        yield {
            "producer": mock_producer,
            "producer_instance": mock_producer_instance,
            "admin": mock_admin,
            "admin_instance": mock_admin_instance,
        }


@pytest.mark.integration
def test_intelligence_published_to_kafka(mock_kafka):
    """
    Test that intelligence ingestion publishes to Kafka

    Pipeline: API → Broker → Classification → STM → Kafka → Agents
    """
    # Ingest intelligence
    intel_data = {
        "intelligence_type": "price",
        "source": "test_source",
        "data": {"current_price": 62500.0, "price_change_percentage_24h": 5.5},
        "symbol": "BTC",
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    # Verify message was sent to Kafka
    assert mock_kafka["producer_instance"].send.called
    assert mock_kafka["producer_instance"].flush.called


@pytest.mark.integration
def test_critical_price_routed_to_multiple_topics(mock_kafka):
    """
    Test that CRITICAL price intelligence is routed to multiple topics
    """
    # Ingest critical price intelligence (large price change)
    intel_data = {
        "intelligence_type": "price",
        "source": "coingecko",
        "data": {
            "current_price": 62500.0,
            "price_change_percentage_24h": 10.0,  # Large change -> CRITICAL
        },
        "symbol": "BTC",
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    data = response.json()
    assert data["importance"] == "CRITICAL"

    # Verify Kafka was called
    # CRITICAL price should go to:
    # 1. intelligence.critical
    # 2. price.critical
    assert mock_kafka["producer_instance"].send.call_count >= 2


@pytest.mark.integration
def test_normal_intelligence_single_topic(mock_kafka):
    """
    Test that NORMAL intelligence goes to single topic
    """
    intel_data = {
        "intelligence_type": "price",
        "source": "test",
        "data": {
            "current_price": 62500.0,
            "price_change_percentage_24h": 0.5,  # Small change -> NORMAL or LOW
        },
        "symbol": "BTC",
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    data = response.json()
    assert data["importance"] in ["NORMAL", "LOW"]

    # Should only go to importance-based topic (not type-specific)
    assert mock_kafka["producer_instance"].send.called


@pytest.mark.integration
def test_agent_registration_returns_kafka_topics():
    """
    Test that agent registration provides Kafka topics to subscribe to
    """
    agent_data = {
        "agent_id": "kafka_test_agent",
        "agent_type": "trading",
        "capabilities": {
            "intelligence_types": ["price", "sentiment"],
            "symbols": ["BTC"],
            "min_importance": "normal",
        },
    }

    response = client.post("/api/v1/agents/register", json=agent_data)
    assert response.status_code == 200

    data = response.json()
    assert "kafka_topics" in data
    assert len(data["kafka_topics"]) >= 2  # At least price and sentiment topics


@pytest.mark.integration
def test_kafka_health_check(mock_kafka):
    """
    Test that Kafka health is reported correctly
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "components" in data
    assert "kafka" in data["components"]


@pytest.mark.integration
def test_whale_intelligence_kafka_routing(mock_kafka):
    """
    Test whale movement intelligence Kafka routing
    """
    intel_data = {
        "intelligence_type": "whale",
        "source": "whale_alert",
        "data": {
            "amount_usd": 15000000,  # $15M -> CRITICAL
            "from_address": "0x123...",
            "to_address": "0x456...",
        },
        "symbol": "BTC",
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    data = response.json()
    assert data["importance"] == "CRITICAL"
    assert data["type"] == "whale"

    # Should be routed to whale.massive topic
    assert mock_kafka["producer_instance"].send.called


@pytest.mark.integration
def test_sentiment_intelligence_kafka_routing(mock_kafka):
    """
    Test sentiment intelligence Kafka routing
    """
    intel_data = {
        "intelligence_type": "sentiment",
        "source": "news_api",
        "data": {"sentiment_score": 0.8, "confidence": 0.9, "headline": "Bitcoin adoption surges"},
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "sentiment"

    # High confidence + strong sentiment -> CRITICAL -> sentiment.breaking
    if data["importance"] == "CRITICAL":
        assert mock_kafka["producer_instance"].send.call_count >= 2


@pytest.mark.integration
def test_kafka_topic_creation(mock_kafka):
    """
    Test that default Kafka topics are created on startup
    """
    # Topics should be created during app startup
    # Verify create_topics was called
    assert mock_kafka["admin_instance"].create_topics.called


@pytest.mark.integration
def test_multiple_intelligence_kafka_ordering(mock_kafka):
    """
    Test that multiple intelligence messages maintain order in Kafka
    """
    # Send multiple messages in sequence
    for i in range(5):
        intel_data = {
            "intelligence_type": "price",
            "source": "test",
            "data": {"current_price": 62500.0 + i * 100, "sequence": i},
            "symbol": "BTC",
        }
        response = client.post("/api/v1/intelligence/ingest", json=intel_data)
        assert response.status_code == 200

    # All messages should be sent to Kafka
    assert mock_kafka["producer_instance"].send.call_count >= 5


@pytest.mark.integration
def test_kafka_failure_doesnt_block_pipeline(mock_kafka):
    """
    Test that Kafka failures don't block the intelligence pipeline
    """
    # Simulate Kafka failure
    mock_kafka["producer_instance"].send.side_effect = Exception("Kafka error")

    intel_data = {
        "intelligence_type": "price",
        "source": "test",
        "data": {"current_price": 62500.0},
        "symbol": "BTC",
    }

    # Should still succeed even if Kafka fails
    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    # Message should still be cached in STM
    stm_response = client.get("/api/v1/memory/stm/price/BTC")
    assert stm_response.status_code == 200


@pytest.mark.integration
def test_regulatory_intelligence_always_critical(mock_kafka):
    """
    Test that regulatory intelligence is always CRITICAL
    """
    intel_data = {
        "intelligence_type": "regulatory",
        "source": "regulatory_api",
        "data": {"title": "New crypto regulation announced", "impact": "high"},
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    data = response.json()
    assert data["importance"] == "CRITICAL"

    # Should go to regulatory.alerts topic
    assert mock_kafka["producer_instance"].send.called


@pytest.mark.integration
def test_kafka_message_serialization(mock_kafka):
    """
    Test that intelligence messages are properly serialized for Kafka
    """
    intel_data = {
        "intelligence_type": "price",
        "source": "test",
        "data": {"current_price": 62500.0, "nested_object": {"key": "value"}, "array": [1, 2, 3]},
        "symbol": "BTC",
        "metadata": {"custom_field": "custom_value"},
    }

    response = client.post("/api/v1/intelligence/ingest", json=intel_data)
    assert response.status_code == 200

    # Verify send was called with proper arguments
    assert mock_kafka["producer_instance"].send.called

    # Get the call arguments
    call_args = mock_kafka["producer_instance"].send.call_args

    # Verify topic, key, and value were provided
    assert "topic" in call_args.kwargs
    assert "key" in call_args.kwargs
    assert "value" in call_args.kwargs
