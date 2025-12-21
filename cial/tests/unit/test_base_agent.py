"""
Unit tests for Base Agent
"""

import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest

from agents.base_agent import AgentDecision, AgentDecisionType, BaseAgent
from api.models.intelligence import (
    AgentCapabilities,
    AgentStatus,
    AgentType,
    IntelligenceImportance,
    IntelligenceMessage,
    IntelligenceType,
)


class TestAgent(BaseAgent):
    """Test agent implementation for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_messages = []
        self.executed_decisions = []

    async def process_intelligence(self, message):
        """Store processed messages."""
        self.processed_messages.append(message)
        return AgentDecision(
            decision_type=AgentDecisionType.ANALYZE, confidence=0.8, reasoning="Test decision"
        )

    async def execute_decision(self, decision):
        """Store executed decisions."""
        self.executed_decisions.append(decision)


@pytest.fixture
def agent_capabilities():
    """Create test agent capabilities."""
    return AgentCapabilities(
        intelligence_types=[IntelligenceType.PRICE, IntelligenceType.SENTIMENT],
        symbols=["BTC", "ETH"],
        min_importance=IntelligenceImportance.NORMAL,
        real_time=True,
    )


@pytest.fixture
def test_agent(agent_capabilities):
    """Create test agent instance."""
    with (
        patch("agents.base_agent.get_short_term_memory"),
        patch("agents.base_agent.get_long_term_memory"),
    ):

        agent = TestAgent(
            agent_id="test_agent_001", agent_type=AgentType.TRADING, capabilities=agent_capabilities
        )
        return agent


@pytest.fixture
def sample_intelligence():
    """Create sample intelligence message."""
    return IntelligenceMessage(
        id="test_msg_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test_source",
        symbol="BTC",
        data={"current_price": 62500.0},
        metadata={},
        timestamp=datetime.utcnow(),
        validated=True,
    )


def test_agent_initialization(test_agent, agent_capabilities):
    """Test agent initialization."""
    assert test_agent.agent_id == "test_agent_001"
    assert test_agent.agent_type == AgentType.TRADING
    assert test_agent.capabilities == agent_capabilities
    assert test_agent.status == AgentStatus.INITIALIZING
    assert test_agent._context == {}
    assert test_agent._decisions == []


@pytest.mark.asyncio
async def test_agent_start_stop(test_agent):
    """Test agent lifecycle - start and stop."""
    # Start agent
    await test_agent.start()
    assert test_agent.status == AgentStatus.ACTIVE
    assert test_agent._running is True
    assert test_agent._task is not None

    # Give processing loop time to start
    await asyncio.sleep(0.1)

    # Stop agent
    await test_agent.stop()
    assert test_agent.status == AgentStatus.STOPPED
    assert test_agent._running is False


@pytest.mark.asyncio
async def test_agent_pause_resume(test_agent):
    """Test agent pause and resume."""
    await test_agent.start()

    # Pause
    await test_agent.pause()
    assert test_agent.status == AgentStatus.PAUSED

    # Resume
    await test_agent.resume()
    assert test_agent.status == AgentStatus.ACTIVE

    await test_agent.stop()


@pytest.mark.asyncio
async def test_receive_intelligence(test_agent, sample_intelligence):
    """Test receiving and processing intelligence."""
    await test_agent.start()

    # Send intelligence
    await test_agent.receive_intelligence(sample_intelligence)

    # Wait for processing
    await asyncio.sleep(0.2)

    # Verify processing
    assert len(test_agent.processed_messages) == 1
    assert test_agent.processed_messages[0].id == "test_msg_001"
    assert len(test_agent.executed_decisions) == 1

    await test_agent.stop()


@pytest.mark.asyncio
async def test_intelligence_filtering_by_type(test_agent):
    """Test intelligence filtering by type."""
    await test_agent.start()

    # Should process (PRICE is in capabilities)
    price_message = IntelligenceMessage(
        id="price_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    # Should NOT process (WHALE not in capabilities)
    whale_message = IntelligenceMessage(
        id="whale_001",
        type=IntelligenceType.WHALE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await test_agent.receive_intelligence(price_message)
    await test_agent.receive_intelligence(whale_message)

    await asyncio.sleep(0.2)

    # Only price message should be processed
    assert len(test_agent.processed_messages) == 1
    assert test_agent.processed_messages[0].id == "price_001"

    await test_agent.stop()


@pytest.mark.asyncio
async def test_intelligence_filtering_by_symbol(test_agent):
    """Test intelligence filtering by symbol."""
    await test_agent.start()

    # Should process (BTC in capabilities)
    btc_message = IntelligenceMessage(
        id="btc_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    # Should NOT process (SOL not in capabilities)
    sol_message = IntelligenceMessage(
        id="sol_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="SOL",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await test_agent.receive_intelligence(btc_message)
    await test_agent.receive_intelligence(sol_message)

    await asyncio.sleep(0.2)

    assert len(test_agent.processed_messages) == 1
    assert test_agent.processed_messages[0].symbol == "BTC"

    await test_agent.stop()


@pytest.mark.asyncio
async def test_intelligence_filtering_by_importance(test_agent):
    """Test intelligence filtering by importance threshold."""
    await test_agent.start()

    # Should process (NORMAL >= NORMAL)
    normal_message = IntelligenceMessage(
        id="normal_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        symbol="BTC",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    # Should NOT process (LOW < NORMAL)
    low_message = IntelligenceMessage(
        id="low_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.LOW,
        source="test",
        symbol="BTC",
        data={},
        timestamp=datetime.utcnow(),
        validated=True,
    )

    await test_agent.receive_intelligence(normal_message)
    await test_agent.receive_intelligence(low_message)

    await asyncio.sleep(0.2)

    assert len(test_agent.processed_messages) == 1
    assert test_agent.processed_messages[0].importance == IntelligenceImportance.NORMAL

    await test_agent.stop()


def test_agent_decision_creation():
    """Test AgentDecision creation."""
    decision = AgentDecision(
        decision_type=AgentDecisionType.BUY,
        confidence=0.85,
        reasoning="Price dipped below support",
        data={"symbol": "BTC", "price": 60000},
        metadata={"strategy": "mean_reversion"},
    )

    assert decision.decision_type == AgentDecisionType.BUY
    assert decision.confidence == 0.85
    assert decision.reasoning == "Price dipped below support"
    assert decision.data["symbol"] == "BTC"
    assert decision.metadata["strategy"] == "mean_reversion"
    assert decision.id.startswith("decision_")


def test_agent_decision_to_dict():
    """Test AgentDecision serialization."""
    decision = AgentDecision(decision_type=AgentDecisionType.SELL, confidence=0.9, reasoning="Test")

    decision_dict = decision.to_dict()

    assert decision_dict["decision_type"] == "sell"
    assert decision_dict["confidence"] == 0.9
    assert decision_dict["reasoning"] == "Test"
    assert "id" in decision_dict
    assert "timestamp" in decision_dict


def test_agent_stats(test_agent):
    """Test agent statistics."""
    # Add some mock decisions
    test_agent._decisions = [
        AgentDecision(AgentDecisionType.BUY, 0.8, "Test"),
        AgentDecision(AgentDecisionType.SELL, 0.9, "Test"),
        AgentDecision(AgentDecisionType.BUY, 0.7, "Test"),
    ]

    stats = test_agent.get_stats()

    assert stats["agent_id"] == "test_agent_001"
    assert stats["agent_type"] == "trading"
    assert stats["total_decisions"] == 3
    assert stats["decisions_by_type"]["buy"] == 2
    assert stats["decisions_by_type"]["sell"] == 1
    assert stats["average_confidence"] == 0.8  # (0.8 + 0.9 + 0.7) / 3


def test_agent_context(test_agent):
    """Test agent context management."""
    context = {"last_price": 62500, "trend": "bullish"}
    test_agent._context = context.copy()

    retrieved_context = test_agent.get_context()

    assert retrieved_context == context
    # Verify it's a copy
    retrieved_context["new_key"] = "value"
    assert "new_key" not in test_agent._context


@pytest.mark.asyncio
async def test_agent_not_processing_when_inactive(test_agent, sample_intelligence):
    """Test that agent doesn't process intelligence when not active."""
    # Don't start agent
    assert test_agent.status == AgentStatus.INITIALIZING

    await test_agent.receive_intelligence(sample_intelligence)
    await asyncio.sleep(0.1)

    # Should not process
    assert len(test_agent.processed_messages) == 0


@pytest.mark.asyncio
async def test_context_update_with_intelligence(test_agent, sample_intelligence):
    """Test that agent context is updated with intelligence."""
    with patch.object(test_agent.stm, "store_agent_context") as mock_store:
        await test_agent.start()
        await test_agent.receive_intelligence(sample_intelligence)
        await asyncio.sleep(0.2)

        # Verify context was stored
        assert mock_store.called
        call_args = mock_store.call_args
        assert call_args.kwargs["agent_id"] == "test_agent_001"
        assert "last_price" in call_args.kwargs["context"]

        await test_agent.stop()
