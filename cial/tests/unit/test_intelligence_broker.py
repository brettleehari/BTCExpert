"""
Unit tests for Intelligence Broker
"""

import pytest
from api.models.intelligence import (
    IntelligenceType, IntelligenceImportance, DataConnector
)
from core.intelligence_broker import IntelligenceBroker
from core.agent_registry import AgentRegistry
from api.models.intelligence import AgentRegistration, AgentCapabilities, AgentType


@pytest.fixture
def broker():
    """Create a fresh broker for each test"""
    return IntelligenceBroker()


@pytest.fixture
def broker_with_agent(broker):
    """Broker with a registered agent"""
    registry = broker.agent_registry
    registry.register_agent(AgentRegistration(
        agent_id="test_agent",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(
            intelligence_types=[IntelligenceType.PRICE],
            symbols=["BTC"]
        )
    ))
    return broker


def test_process_price_intelligence(broker):
    """Test processing price intelligence"""
    message = broker.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="coingecko",
        data={
            "current_price": 62500.0,
            "price_change_percentage_24h": 5.5
        },
        symbol="BTC"
    )

    assert message.id is not None
    assert message.type == IntelligenceType.PRICE
    assert message.source == "coingecko"
    assert message.symbol == "BTC"
    assert message.importance == IntelligenceImportance.CRITICAL  # >5% change


def test_classify_price_importance(broker):
    """Test price importance classification"""
    # Critical: >5% change
    msg1 = broker.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="test",
        data={"price_change_percentage_24h": 6.0},
        symbol="BTC"
    )
    assert msg1.importance == IntelligenceImportance.CRITICAL

    # Normal: 1-5% change
    msg2 = broker.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="test",
        data={"price_change_percentage_24h": 2.0},
        symbol="BTC"
    )
    assert msg2.importance == IntelligenceImportance.NORMAL

    # Low: <1% change
    msg3 = broker.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="test",
        data={"price_change_percentage_24h": 0.5},
        symbol="BTC"
    )
    assert msg3.importance == IntelligenceImportance.LOW


def test_classify_whale_importance(broker):
    """Test whale movement importance classification"""
    # Critical: >$10M
    msg1 = broker.process_intelligence(
        intelligence_type=IntelligenceType.WHALE,
        source="whale_alert",
        data={"amount_usd": 15_000_000},
        symbol="BTC"
    )
    assert msg1.importance == IntelligenceImportance.CRITICAL

    # Normal: $1M-$10M
    msg2 = broker.process_intelligence(
        intelligence_type=IntelligenceType.WHALE,
        source="whale_alert",
        data={"amount_usd": 5_000_000},
        symbol="BTC"
    )
    assert msg2.importance == IntelligenceImportance.NORMAL

    # Low: <$1M
    msg3 = broker.process_intelligence(
        intelligence_type=IntelligenceType.WHALE,
        source="whale_alert",
        data={"amount_usd": 500_000},
        symbol="BTC"
    )
    assert msg3.importance == IntelligenceImportance.LOW


def test_routing_to_agents(broker_with_agent):
    """Test intelligence routing to interested agents"""
    message = broker_with_agent.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="coingecko",
        data={"current_price": 62500.0},
        symbol="BTC"
    )

    # Check that agent received the message (activity updated)
    agent = broker_with_agent.agent_registry.get_agent("test_agent")
    assert agent.message_count == 1


def test_register_connector(broker):
    """Test registering data connector"""
    connector = DataConnector(
        connector_id="test_connector",
        name="Test Connector",
        intelligence_types=[IntelligenceType.PRICE],
        reliability_score=0.95
    )

    success = broker.register_connector(connector)
    assert success is True

    retrieved = broker.get_connector("test_connector")
    assert retrieved is not None
    assert retrieved.name == "Test Connector"


def test_get_recent_intelligence(broker):
    """Test retrieving recent intelligence"""
    # Process multiple messages
    for i in range(5):
        broker.process_intelligence(
            intelligence_type=IntelligenceType.PRICE,
            source="test",
            data={"price": 60000 + i * 100},
            symbol="BTC"
        )

    recent = broker.get_recent_intelligence(limit=3)
    assert len(recent) == 3


def test_filter_intelligence_by_type(broker):
    """Test filtering intelligence by type"""
    broker.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="test",
        data={"price": 62500},
        symbol="BTC"
    )

    broker.process_intelligence(
        intelligence_type=IntelligenceType.SENTIMENT,
        source="test",
        data={"sentiment_score": 0.8},
        symbol="BTC"
    )

    price_intel = broker.get_recent_intelligence(intelligence_type=IntelligenceType.PRICE)
    assert len(price_intel) == 1
    assert price_intel[0].type == IntelligenceType.PRICE


def test_broker_stats(broker_with_agent):
    """Test broker statistics"""
    # Process some messages
    for i in range(3):
        broker_with_agent.process_intelligence(
            intelligence_type=IntelligenceType.PRICE,
            source="test",
            data={"price": 60000},
            symbol="BTC"
        )

    stats = broker_with_agent.get_broker_stats()

    assert stats["total_messages_processed"] == 3
    assert "agent_stats" in stats
    assert "routing_stats" in stats
