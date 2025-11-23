"""
Unit tests for Agent Registry
"""

import pytest
from api.models.intelligence import (
    AgentRegistration, AgentCapabilities, AgentType,
    IntelligenceType, AgentStatus
)
from core.agent_registry import AgentRegistry


@pytest.fixture
def registry():
    """Create a fresh registry for each test"""
    return AgentRegistry()


@pytest.fixture
def sample_registration():
    """Sample agent registration"""
    return AgentRegistration(
        agent_id="test_agent_001",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(
            intelligence_types=[IntelligenceType.PRICE, IntelligenceType.SENTIMENT],
            symbols=["BTC", "ETH"],
            min_importance="normal"
        ),
        metadata={"version": "1.0.0"}
    )


def test_register_agent(registry, sample_registration):
    """Test agent registration"""
    agent = registry.register_agent(sample_registration)

    assert agent.agent_id == "test_agent_001"
    assert agent.agent_type == AgentType.TRADING
    assert agent.status == AgentStatus.ACTIVE
    assert len(agent.capabilities.intelligence_types) == 2


def test_register_duplicate_agent(registry, sample_registration):
    """Test that registering duplicate agent fails"""
    registry.register_agent(sample_registration)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_agent(sample_registration)


def test_get_agent(registry, sample_registration):
    """Test retrieving agent by ID"""
    registry.register_agent(sample_registration)

    agent = registry.get_agent("test_agent_001")
    assert agent is not None
    assert agent.agent_id == "test_agent_001"

    missing_agent = registry.get_agent("nonexistent")
    assert missing_agent is None


def test_unregister_agent(registry, sample_registration):
    """Test agent unregistration"""
    registry.register_agent(sample_registration)
    assert registry.get_agent("test_agent_001") is not None

    success = registry.unregister_agent("test_agent_001")
    assert success is True
    assert registry.get_agent("test_agent_001") is None

    # Unregistering again should return False
    success = registry.unregister_agent("test_agent_001")
    assert success is False


def test_update_agent_status(registry, sample_registration):
    """Test updating agent status"""
    registry.register_agent(sample_registration)

    success = registry.update_agent_status(
        "test_agent_001",
        AgentStatus.PAUSED,
        {"reason": "maintenance"}
    )

    assert success is True
    agent = registry.get_agent("test_agent_001")
    assert agent.status == AgentStatus.PAUSED
    assert agent.metadata["reason"] == "maintenance"


def test_get_agents_by_type(registry):
    """Test filtering agents by type"""
    # Register multiple agents
    registry.register_agent(AgentRegistration(
        agent_id="trading_001",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.PRICE])
    ))

    registry.register_agent(AgentRegistration(
        agent_id="risk_001",
        agent_type=AgentType.RISK,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.PRICE])
    ))

    registry.register_agent(AgentRegistration(
        agent_id="trading_002",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.SENTIMENT])
    ))

    trading_agents = registry.get_agents_by_type(AgentType.TRADING)
    assert len(trading_agents) == 2

    risk_agents = registry.get_agents_by_type(AgentType.RISK)
    assert len(risk_agents) == 1


def test_get_agents_for_intelligence(registry):
    """Test finding agents interested in specific intelligence"""
    registry.register_agent(AgentRegistration(
        agent_id="price_agent",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(
            intelligence_types=[IntelligenceType.PRICE],
            symbols=["BTC"]
        )
    ))

    registry.register_agent(AgentRegistration(
        agent_id="sentiment_agent",
        agent_type=AgentType.SENTIMENT,
        capabilities=AgentCapabilities(
            intelligence_types=[IntelligenceType.SENTIMENT],
            symbols=[]  # All symbols
        )
    ))

    # Find agents for BTC price
    price_agents = registry.get_agents_for_intelligence(IntelligenceType.PRICE, "BTC")
    assert len(price_agents) == 1
    assert price_agents[0].agent_id == "price_agent"

    # Find agents for ETH price (price_agent only monitors BTC)
    eth_price_agents = registry.get_agents_for_intelligence(IntelligenceType.PRICE, "ETH")
    assert len(eth_price_agents) == 0

    # Find agents for sentiment (sentiment_agent monitors all symbols)
    sentiment_agents = registry.get_agents_for_intelligence(IntelligenceType.SENTIMENT, "BTC")
    assert len(sentiment_agents) == 1


def test_get_active_agent_count(registry):
    """Test counting active agents"""
    registry.register_agent(AgentRegistration(
        agent_id="agent_1",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.PRICE])
    ))

    registry.register_agent(AgentRegistration(
        agent_id="agent_2",
        agent_type=AgentType.RISK,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.PRICE])
    ))

    assert registry.get_active_agent_count() == 2

    # Pause one agent
    registry.update_agent_status("agent_1", AgentStatus.PAUSED)
    assert registry.get_active_agent_count() == 1


def test_get_registry_stats(registry):
    """Test registry statistics"""
    # Register multiple agents
    registry.register_agent(AgentRegistration(
        agent_id="agent_1",
        agent_type=AgentType.TRADING,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.PRICE])
    ))

    registry.register_agent(AgentRegistration(
        agent_id="agent_2",
        agent_type=AgentType.RISK,
        capabilities=AgentCapabilities(intelligence_types=[IntelligenceType.SENTIMENT])
    ))

    stats = registry.get_registry_stats()

    assert stats["total_agents"] == 2
    assert stats["active_agents"] == 2
    assert "status_breakdown" in stats
    assert "type_breakdown" in stats
