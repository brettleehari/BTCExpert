"""
Integration tests for complete Agent Pipeline
Tests the full flow: Intelligence → Broker → Agent → Decision → Execution
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from agents.sample_price_monitor_agent import PriceMonitorAgent
from api.models.intelligence import IntelligenceImportance, IntelligenceMessage, IntelligenceType


@pytest.fixture
def mock_memory():
    """Mock memory systems."""
    with (
        patch("agents.base_agent.get_short_term_memory") as mock_stm,
        patch("agents.base_agent.get_long_term_memory") as mock_ltm,
    ):

        mock_stm_instance = Mock()
        mock_ltm_instance = Mock()

        mock_stm_instance.store_agent_context = Mock()
        mock_stm_instance.store_agent_decision = Mock()
        mock_stm_instance.get_current_price = Mock(
            return_value={"current_price": 62500.0, "price_change_percentage_24h": 2.5}
        )
        mock_stm_instance.get_agent_decisions = Mock(return_value=[])

        mock_ltm_instance.get_historical_prices = Mock(return_value=[])

        mock_stm.return_value = mock_stm_instance
        mock_ltm.return_value = mock_ltm_instance

        yield {"stm": mock_stm_instance, "ltm": mock_ltm_instance}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_agent_pipeline(mock_memory):
    """
    Test complete pipeline: Intelligence → Agent → Decision → Execution

    Pipeline Flow:
    1. Create agent with specific capabilities
    2. Start agent processing loop
    3. Send intelligence to agent
    4. Agent processes and makes decision
    5. Decision is executed and stored
    """
    # Create price monitor agent
    agent = PriceMonitorAgent(
        agent_id="integration_test_agent",
        symbols=["BTC"],
        alert_threshold=5.0,
        recommendation_threshold=10.0,
    )

    # Start agent
    await agent.start()

    # Create intelligence message
    intelligence = IntelligenceMessage(
        id="test_price_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.CRITICAL,
        source="coingecko",
        symbol="BTC",
        data={
            "current_price": 70000.0,  # 12% increase from baseline (62500)
            "price_change_percentage_24h": 12.0,
            "volume_24h": 35000000000,
            "market_cap": 1400000000000,
        },
        metadata={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    # Send intelligence to agent
    await agent.receive_intelligence(intelligence)

    # Wait for processing
    await asyncio.sleep(0.3)

    # Verify decision was made
    stats = agent.get_stats()
    assert stats["total_decisions"] >= 1

    # Verify decision type (should be SELL due to high price increase)
    decisions = stats["decisions_by_type"]
    assert "sell" in decisions or "alert" in decisions

    # Verify decision was stored
    assert mock_memory["stm"].store_agent_decision.called

    # Stop agent
    await agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_alert_generation(mock_memory):
    """Test that agent generates alerts on moderate price changes."""
    agent = PriceMonitorAgent(agent_id="alert_test_agent", symbols=["ETH"], alert_threshold=5.0)

    await agent.start()

    # Moderate price change (should trigger alert)
    intelligence = IntelligenceMessage(
        id="test_eth_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="coingecko",
        symbol="ETH",
        data={
            "current_price": 3300.0,  # 6.5% increase from baseline (3100)
            "price_change_percentage_24h": 6.5,
            "volume_24h": 18000000000,
            "market_cap": 400000000000,
        },
        metadata={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await agent.receive_intelligence(intelligence)
    await asyncio.sleep(0.3)

    # Should have generated an alert
    stats = agent.get_stats()
    assert stats["total_decisions"] >= 1

    await agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_filters_by_symbol(mock_memory):
    """Test that agent only processes intelligence for configured symbols."""
    agent = PriceMonitorAgent(
        agent_id="filter_test_agent", symbols=["BTC"], alert_threshold=5.0  # Only BTC
    )

    await agent.start()

    # BTC intelligence (should process)
    btc_intelligence = IntelligenceMessage(
        id="btc_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={"current_price": 63000.0, "price_change_percentage_24h": 1.0},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    # ETH intelligence (should NOT process)
    eth_intelligence = IntelligenceMessage(
        id="eth_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="ETH",
        data={"current_price": 3200.0, "price_change_percentage_24h": 1.0},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await agent.receive_intelligence(btc_intelligence)
    await agent.receive_intelligence(eth_intelligence)

    await asyncio.sleep(0.3)

    # Should only process BTC
    assert len(agent.processed_messages) == 1
    assert agent.processed_messages[0].symbol == "BTC"

    await agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_context_persistence(mock_memory):
    """Test that agent context is persisted to STM."""
    agent = PriceMonitorAgent(agent_id="context_test_agent", symbols=["BTC"])

    await agent.start()

    intelligence = IntelligenceMessage(
        id="context_test_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={"current_price": 62500.0},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await agent.receive_intelligence(intelligence)
    await asyncio.sleep(0.3)

    # Verify context was stored
    assert mock_memory["stm"].store_agent_context.called

    # Get agent context
    context = agent.get_context()
    assert "last_price" in context
    assert "symbol_BTC" in context

    await agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_decision_tracking(mock_memory):
    """Test that agent decisions are tracked and accessible."""
    agent = PriceMonitorAgent(
        agent_id="decision_track_agent", symbols=["BTC"], recommendation_threshold=5.0
    )

    await agent.start()

    # Send intelligence that should trigger decision
    intelligence = IntelligenceMessage(
        id="decision_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.CRITICAL,
        source="test",
        symbol="BTC",
        data={"current_price": 70000.0, "price_change_percentage_24h": 12.0},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await agent.receive_intelligence(intelligence)
    await asyncio.sleep(0.3)

    # Get stats
    stats = agent.get_stats()

    assert stats["total_decisions"] >= 1
    assert stats["average_confidence"] > 0
    assert len(stats["decisions_by_type"]) > 0

    await agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_baseline_reset(mock_memory):
    """Test agent baseline reset functionality."""
    agent = PriceMonitorAgent(agent_id="baseline_test_agent", symbols=["BTC"])

    await agent.start()

    # Get initial baseline
    baselines_before = agent.get_baselines()
    assert "BTC" in baselines_before
    initial_baseline = baselines_before["BTC"]

    # Reset baseline
    mock_memory["stm"].get_current_price = Mock(return_value={"current_price": 70000.0})

    await agent.reset_baseline("BTC")

    # Verify baseline changed
    baselines_after = agent.get_baselines()
    assert baselines_after["BTC"] == 70000.0
    assert baselines_after["BTC"] != initial_baseline

    await agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_agents_parallel_processing(mock_memory):
    """Test multiple agents processing intelligence in parallel."""
    # Create multiple agents
    agent1 = PriceMonitorAgent(agent_id="parallel_agent_1", symbols=["BTC"], alert_threshold=5.0)

    agent2 = PriceMonitorAgent(agent_id="parallel_agent_2", symbols=["ETH"], alert_threshold=5.0)

    # Start both agents
    await agent1.start()
    await agent2.start()

    # Send intelligence to both
    btc_intel = IntelligenceMessage(
        id="parallel_btc",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={"current_price": 63000.0, "price_change_percentage_24h": 1.0},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    eth_intel = IntelligenceMessage(
        id="parallel_eth",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="ETH",
        data={"current_price": 3200.0, "price_change_percentage_24h": 1.0},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await agent1.receive_intelligence(btc_intel)
    await agent2.receive_intelligence(eth_intel)

    await asyncio.sleep(0.3)

    # Both agents should have processed
    assert len(agent1.processed_messages) >= 1
    assert len(agent2.processed_messages) >= 1

    # Stop both agents
    await agent1.stop()
    await agent2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_lifecycle_transitions(mock_memory):
    """Test agent lifecycle state transitions."""
    agent = PriceMonitorAgent(agent_id="lifecycle_test_agent", symbols=["BTC"])

    # Initial state
    from api.models.intelligence import AgentStatus

    assert agent.status == AgentStatus.INITIALIZING

    # Start -> Active
    await agent.start()
    assert agent.status == AgentStatus.ACTIVE

    # Active -> Paused
    await agent.pause()
    assert agent.status == AgentStatus.PAUSED

    # Paused -> Active
    await agent.resume()
    assert agent.status == AgentStatus.ACTIVE

    # Active -> Stopped
    await agent.stop()
    assert agent.status == AgentStatus.STOPPED
