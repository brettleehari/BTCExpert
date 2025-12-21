"""
Unit tests for Kafka Manager
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from api.models.intelligence import IntelligenceImportance, IntelligenceMessage, IntelligenceType
from infrastructure.kafka_manager import KafkaManager


@pytest.fixture
def mock_kafka_dependencies():
    """Mock Kafka dependencies"""
    with (
        patch("infrastructure.kafka_manager.KafkaProducer") as mock_producer,
        patch("infrastructure.kafka_manager.KafkaAdminClient") as mock_admin,
    ):

        mock_producer_instance = MagicMock()
        mock_admin_instance = MagicMock()

        mock_producer.return_value = mock_producer_instance
        mock_admin.return_value = mock_admin_instance

        yield {
            "producer": mock_producer,
            "producer_instance": mock_producer_instance,
            "admin": mock_admin,
            "admin_instance": mock_admin_instance,
        }


@pytest.fixture
def kafka_manager(mock_kafka_dependencies):
    """Create KafkaManager instance with mocked dependencies"""
    manager = KafkaManager()
    manager.connect()
    return manager


@pytest.fixture
def sample_message():
    """Create sample intelligence message"""
    return IntelligenceMessage(
        id="test_msg_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.CRITICAL,
        source="test_source",
        symbol="BTC",
        data={"current_price": 62500.0, "price_change_percentage_24h": 5.5},
        metadata={},
        timestamp=datetime.utcnow(),
        validated=True,
    )


def test_kafka_manager_initialization(mock_kafka_dependencies):
    """Test Kafka manager initialization"""
    manager = KafkaManager()
    assert manager._producer is None
    assert manager._admin_client is None
    assert manager._connected is False


def test_kafka_connect(mock_kafka_dependencies):
    """Test Kafka connection"""
    manager = KafkaManager()
    manager.connect()

    assert manager._connected is True
    mock_kafka_dependencies["producer"].assert_called_once()
    mock_kafka_dependencies["admin"].assert_called_once()


def test_kafka_disconnect(kafka_manager, mock_kafka_dependencies):
    """Test Kafka disconnection"""
    kafka_manager.disconnect()

    assert kafka_manager._connected is False
    mock_kafka_dependencies["producer_instance"].flush.assert_called_once()
    mock_kafka_dependencies["producer_instance"].close.assert_called_once()
    mock_kafka_dependencies["admin_instance"].close.assert_called_once()


def test_publish_intelligence_success(kafka_manager, sample_message, mock_kafka_dependencies):
    """Test successful intelligence publishing"""
    mock_future = MagicMock()
    mock_kafka_dependencies["producer_instance"].send.return_value = mock_future

    result = kafka_manager.publish_intelligence(sample_message)

    assert result is True
    mock_kafka_dependencies["producer_instance"].send.assert_called()
    mock_kafka_dependencies["producer_instance"].flush.assert_called()


def test_publish_intelligence_not_connected():
    """Test publishing when not connected"""
    manager = KafkaManager()
    message = IntelligenceMessage(
        id="test",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    result = manager.publish_intelligence(message)
    assert result is False


def test_get_topics_for_critical_price(kafka_manager):
    """Test topic selection for CRITICAL price intelligence"""
    message = IntelligenceMessage(
        id="test",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.CRITICAL,
        source="test",
        symbol="BTC",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    topics = kafka_manager._get_topics_for_message(message)

    assert "intelligence.critical" in topics
    assert "price.critical" in topics
    assert len(topics) == 2


def test_get_topics_for_normal_price(kafka_manager):
    """Test topic selection for NORMAL price intelligence"""
    message = IntelligenceMessage(
        id="test",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    topics = kafka_manager._get_topics_for_message(message)

    assert "intelligence.normal" in topics
    assert "price.critical" not in topics
    assert len(topics) == 1


def test_get_topics_for_critical_sentiment(kafka_manager):
    """Test topic selection for CRITICAL sentiment intelligence"""
    message = IntelligenceMessage(
        id="test",
        type=IntelligenceType.SENTIMENT,
        importance=IntelligenceImportance.CRITICAL,
        source="test",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    topics = kafka_manager._get_topics_for_message(message)

    assert "intelligence.critical" in topics
    assert "sentiment.breaking" in topics


def test_get_topics_for_critical_whale(kafka_manager):
    """Test topic selection for CRITICAL whale intelligence"""
    message = IntelligenceMessage(
        id="test",
        type=IntelligenceType.WHALE,
        importance=IntelligenceImportance.CRITICAL,
        source="test",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    topics = kafka_manager._get_topics_for_message(message)

    assert "intelligence.critical" in topics
    assert "whale.massive" in topics


def test_get_topics_for_low_importance(kafka_manager):
    """Test topic selection for LOW importance intelligence"""
    message = IntelligenceMessage(
        id="test",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.LOW,
        source="test",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    topics = kafka_manager._get_topics_for_message(message)

    assert "intelligence.low" in topics
    assert len(topics) == 1


def test_create_topic(kafka_manager, mock_kafka_dependencies):
    """Test topic creation"""
    result = kafka_manager.create_topic("test.topic", num_partitions=3, replication_factor=1)

    assert result is True
    mock_kafka_dependencies["admin_instance"].create_topics.assert_called()


def test_get_topics(kafka_manager, mock_kafka_dependencies):
    """Test getting list of topics"""
    mock_kafka_dependencies["admin_instance"].list_topics.return_value = ["topic1", "topic2"]

    topics = kafka_manager.get_topics()

    assert len(topics) == 2
    assert "topic1" in topics
    assert "topic2" in topics


def test_create_consumer(kafka_manager, mock_kafka_dependencies):
    """Test consumer creation"""
    with patch("infrastructure.kafka_manager.KafkaConsumer") as mock_consumer:
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance

        consumer = kafka_manager.create_consumer(
            topics=["price.critical", "sentiment.breaking"], group_id="test-group"
        )

        assert consumer is not None
        mock_consumer.assert_called_once()


def test_is_connected(kafka_manager):
    """Test connection status check"""
    assert kafka_manager.is_connected() is True


def test_get_info_when_connected(kafka_manager, mock_kafka_dependencies):
    """Test getting Kafka info when connected"""
    mock_kafka_dependencies["admin_instance"].list_topics.return_value = ["topic1", "topic2"]

    info = kafka_manager.get_info()

    assert info["connected"] is True
    assert "bootstrap_servers" in info
    assert info["total_topics"] == 2


def test_get_info_when_disconnected():
    """Test getting Kafka info when disconnected"""
    manager = KafkaManager()

    info = manager.get_info()

    assert info["connected"] is False


def test_publish_with_custom_topics(kafka_manager, sample_message, mock_kafka_dependencies):
    """Test publishing to custom topics"""
    mock_future = MagicMock()
    mock_kafka_dependencies["producer_instance"].send.return_value = mock_future

    custom_topics = ["custom.topic1", "custom.topic2"]
    result = kafka_manager.publish_intelligence(sample_message, topics=custom_topics)

    assert result is True
    assert mock_kafka_dependencies["producer_instance"].send.call_count == 2


def test_on_send_success_callback(kafka_manager):
    """Test success callback"""
    record_metadata = MagicMock()
    record_metadata.partition = 0
    record_metadata.offset = 123

    # Should not raise exception
    kafka_manager._on_send_success(record_metadata, "test.topic", "msg_001")


def test_on_send_error_callback(kafka_manager):
    """Test error callback"""
    # Should not raise exception
    kafka_manager._on_send_error(Exception("Test error"), "test.topic", "msg_001")


def test_publish_intelligence_error_handling(
    kafka_manager, sample_message, mock_kafka_dependencies
):
    """Test error handling during publishing"""
    mock_kafka_dependencies["producer_instance"].send.side_effect = Exception("Kafka error")

    result = kafka_manager.publish_intelligence(sample_message)

    assert result is False
