"""
Unit tests for Short-Term Memory (STM)
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from api.models.intelligence import IntelligenceImportance, IntelligenceMessage, IntelligenceType
from memory.short_term_memory import ShortTermMemory


@pytest.fixture
def stm():
    """Create STM instance with mocked Redis"""
    with patch("memory.short_term_memory.get_redis_manager") as mock_redis_manager:
        mock_client = Mock()
        mock_redis_manager.return_value.client = mock_client

        stm = ShortTermMemory()
        stm.redis.client = mock_client
        yield stm


@pytest.fixture
def sample_message():
    """Create sample intelligence message"""
    return IntelligenceMessage(
        id="test_msg_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test_source",
        symbol="BTC",
        data={"current_price": 62500.0, "price_change_percentage_24h": 2.5},
        timestamp=datetime.utcnow(),
    )


def test_cache_intelligence(stm, sample_message):
    """Test caching intelligence message"""
    stm.redis.client.setex = Mock(return_value=True)
    stm.redis.client.zadd = Mock(return_value=1)
    stm.redis.client.expire = Mock(return_value=True)

    result = stm.cache_intelligence(sample_message)

    assert result is True
    assert stm.redis.client.setex.called
    assert stm.redis.client.zadd.called


def test_get_intelligence(stm, sample_message):
    """Test retrieving cached intelligence"""
    stm.redis.client.get = Mock(return_value=sample_message.model_dump_json())

    result = stm.get_intelligence("test_msg_001", IntelligenceType.PRICE, "BTC")

    assert result is not None
    assert result.id == "test_msg_001"
    assert result.symbol == "BTC"


def test_get_intelligence_not_found(stm):
    """Test retrieving non-existent intelligence"""
    stm.redis.client.get = Mock(return_value=None)

    result = stm.get_intelligence("nonexistent", IntelligenceType.PRICE, "BTC")

    assert result is None


def test_store_agent_context(stm):
    """Test storing agent context"""
    stm.redis.client.setex = Mock(return_value=True)

    context = {"last_decision": "buy", "market_state": "bullish"}
    result = stm.store_agent_context("agent_001", context, ttl=3600)

    assert result is True
    stm.redis.client.setex.assert_called_once()


def test_get_agent_context(stm):
    """Test retrieving agent context"""
    _expected_context = {"last_decision": "buy", "market_state": "bullish"}
    stm.redis.client.get = Mock(return_value='{"last_decision": "buy", "market_state": "bullish"}')

    result = stm.get_agent_context("agent_001")

    assert result is not None
    assert result["last_decision"] == "buy"
    assert result["market_state"] == "bullish"


def test_store_agent_decision(stm):
    """Test storing agent decision"""
    stm.redis.client.setex = Mock(return_value=True)
    stm.redis.client.zadd = Mock(return_value=1)
    stm.redis.client.expire = Mock(return_value=True)

    decision = {"id": "decision_001", "action": "buy", "amount": 0.1}
    result = stm.store_agent_decision("agent_001", decision)

    assert result is True
    assert stm.redis.client.setex.called
    assert stm.redis.client.zadd.called


def test_get_agent_decisions(stm):
    """Test retrieving agent decisions"""
    stm.redis.client.zrevrange = Mock(return_value=["decision_001", "decision_002"])
    stm.redis.client.get = Mock(
        side_effect=[
            '{"id": "decision_001", "action": "buy"}',
            '{"id": "decision_002", "action": "sell"}',
        ]
    )

    decisions = stm.get_agent_decisions("agent_001", limit=2)

    assert len(decisions) == 2
    assert decisions[0]["id"] == "decision_001"
    assert decisions[1]["id"] == "decision_002"


def test_store_market_state(stm):
    """Test storing market state"""
    stm.redis.client.setex = Mock(return_value=True)

    state = {"trend": "bullish", "volatility": "low"}
    result = stm.store_market_state(state)

    assert result is True
    stm.redis.client.setex.assert_called_once()


def test_get_market_state(stm):
    """Test retrieving market state"""
    stm.redis.client.get = Mock(return_value='{"trend": "bullish", "volatility": "low"}')

    state = stm.get_market_state()

    assert state is not None
    assert state["trend"] == "bullish"
    assert state["volatility"] == "low"


def test_clear_agent_data(stm):
    """Test clearing all agent data"""
    stm.redis.client.delete = Mock(return_value=2)

    result = stm.clear_agent_data("agent_001")

    assert result is True
    assert stm.redis.client.delete.call_count == 2  # context + decisions


def test_get_ttl_for_type(stm):
    """Test TTL calculation for different intelligence types"""
    with patch("memory.short_term_memory.settings") as mock_settings:
        mock_settings.TTL_LIVE_PRICES = 86400
        mock_settings.TTL_SENTIMENT = 86400
        mock_settings.TTL_WHALE_MOVEMENTS = 604800

        price_ttl = stm._get_ttl_for_type(IntelligenceType.PRICE)
        sentiment_ttl = stm._get_ttl_for_type(IntelligenceType.SENTIMENT)
        whale_ttl = stm._get_ttl_for_type(IntelligenceType.WHALE)

        assert price_ttl == 86400
        assert sentiment_ttl == 86400
        assert whale_ttl == 604800


def test_get_current_price(stm):
    """Test getting current cached price"""
    stm.redis.client.zrevrange = Mock(return_value=["msg_001"])

    message = IntelligenceMessage(
        id="msg_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={"current_price": 62500.0},
        timestamp=datetime.utcnow(),
    )

    stm.redis.client.get = Mock(return_value=message.model_dump_json())

    price_data = stm.get_current_price("BTC")

    assert price_data is not None
    assert price_data["current_price"] == 62500.0
