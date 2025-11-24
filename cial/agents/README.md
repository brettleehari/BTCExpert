# CIAL Agents Framework

Standardized framework for building intelligent cryptocurrency trading agents on top of CIAL.

## Overview

The CIAL Agents Framework provides a robust foundation for creating autonomous agents that:
- Consume intelligence from the CIAL pipeline
- Make data-driven decisions
- Execute actions based on market conditions
- Learn and adapt over time
- Maintain context and state

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CIAL Intelligence Broker              │
│         (Classification, Routing, Distribution)          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        │ Intelligence Messages
                        │
           ┌────────────┴────────────┐
           │                         │
           ▼                         ▼
    ┌─────────────┐          ┌─────────────┐
    │   Agent 1   │          │   Agent 2   │
    │  (Trading)  │          │  (Risk)     │
    └─────────────┘          └─────────────┘
           │                         │
           │ Decisions               │ Decisions
           │                         │
           ▼                         ▼
    ┌─────────────────────────────────────┐
    │      Short-Term Memory (Redis)       │
    │   Long-Term Memory (PostgreSQL)      │
    └──────────────────────────────────────┘
```

## Core Components

### BaseAgent

Abstract base class that all CIAL agents inherit from.

**Key Features:**
- Lifecycle management (start, stop, pause, resume)
- Intelligence filtering by type, symbol, importance
- Automatic context management
- Decision tracking and persistence
- Memory system integration (STM/LTM)
- Asynchronous processing loop

**Lifecycle:**
```
INITIALIZING → ACTIVE ⇄ PAUSED → STOPPED
```

### AgentDecision

Standardized representation of agent decisions.

**Decision Types:**
- `BUY` - Buy recommendation
- `SELL` - Sell recommendation
- `HOLD` - Hold position
- `ALERT` - Generate alert/notification
- `ANALYZE` - Request deeper analysis
- `LEARN` - Store learning outcome

**Properties:**
- `decision_type`: Type of decision
- `confidence`: Confidence level (0.0-1.0)
- `reasoning`: Human-readable explanation
- `data`: Decision-specific data
- `metadata`: Additional metadata
- `timestamp`: When decision was made

## Creating a Custom Agent

### 1. Basic Structure

```python
from agents.base_agent import BaseAgent, AgentDecision, AgentDecisionType
from api.models.intelligence import IntelligenceMessage, AgentType, AgentCapabilities

class MyCustomAgent(BaseAgent):
    def __init__(self, agent_id: str, **kwargs):
        capabilities = AgentCapabilities(
            intelligence_types=[IntelligenceType.PRICE, IntelligenceType.SENTIMENT],
            symbols=["BTC", "ETH"],
            min_importance=IntelligenceImportance.NORMAL,
            real_time=True
        )

        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.TRADING,
            capabilities=capabilities
        )

    async def process_intelligence(self, message: IntelligenceMessage):
        """Process intelligence and make decision."""
        # Your decision logic here
        return AgentDecision(
            decision_type=AgentDecisionType.BUY,
            confidence=0.85,
            reasoning="Price below support level"
        )

    async def execute_decision(self, decision: AgentDecision):
        """Execute the decision."""
        # Your execution logic here
        pass
```

### 2. Lifecycle Hooks

```python
class MyAgent(BaseAgent):
    async def on_start(self):
        """Called when agent starts."""
        # Initialize resources, load models, etc.
        pass

    async def on_stop(self):
        """Called when agent stops."""
        # Cleanup resources
        pass

    async def on_pause(self):
        """Called when agent pauses."""
        pass

    async def on_resume(self):
        """Called when agent resumes."""
        pass
```

### 3. Memory Access

```python
class MyAgent(BaseAgent):
    async def process_intelligence(self, message: IntelligenceMessage):
        # Get current price from STM
        current_price = await self.get_current_price("BTC")

        # Get historical data from LTM
        history = await self.get_price_history("BTC", days=7)

        # Get recent decisions
        decisions = await self.get_recent_decisions(limit=10)

        # Access agent context
        context = self.get_context()

        # Make decision...
```

## Sample Implementation: PriceMonitorAgent

A complete example demonstrating the framework:

```python
from agents.sample_price_monitor_agent import PriceMonitorAgent

# Create agent
agent = PriceMonitorAgent(
    agent_id="btc_monitor",
    symbols=["BTC", "ETH"],
    alert_threshold=5.0,       # Alert on 5% change
    recommendation_threshold=10.0  # Recommend on 10% change
)

# Start agent
await agent.start()

# Agent will now process intelligence automatically

# Get agent statistics
stats = agent.get_stats()
print(f"Total decisions: {stats['total_decisions']}")
print(f"Average confidence: {stats['average_confidence']}")

# Reset baseline prices
await agent.reset_baseline("BTC")

# Stop agent
await agent.stop()
```

## Agent Capabilities

Configure what intelligence your agent can process:

```python
AgentCapabilities(
    intelligence_types=[
        IntelligenceType.PRICE,      # Price updates
        IntelligenceType.SENTIMENT,  # News sentiment
        IntelligenceType.WHALE,      # Whale movements
        IntelligenceType.TECHNICAL,  # Technical indicators
    ],
    symbols=["BTC", "ETH", "SOL"],  # Which symbols to monitor
    min_importance=IntelligenceImportance.NORMAL,  # Importance filter
    real_time=True  # Real-time processing
)
```

## Intelligence Filtering

Agents automatically filter intelligence based on capabilities:

1. **Type Filter**: Only process specified intelligence types
2. **Symbol Filter**: Only process specified symbols
3. **Importance Filter**: Only process intelligence above threshold
4. **Status Filter**: Only process when agent is ACTIVE

## Decision Tracking

All decisions are automatically:
- Assigned unique IDs
- Timestamped
- Stored in agent's decision history
- Persisted to Short-Term Memory
- Available for analysis

## Best Practices

### 1. Single Responsibility
Each agent should focus on one specific task (e.g., price monitoring, risk management, sentiment analysis).

### 2. Confidence Levels
Always provide realistic confidence levels (0.0-1.0) in decisions.

### 3. Clear Reasoning
Provide human-readable explanations for decisions.

### 4. Error Handling
Handle exceptions gracefully in `process_intelligence()` and `execute_decision()`.

### 5. Resource Cleanup
Implement `on_stop()` to clean up resources (connections, files, etc.).

### 6. Testing
Write unit tests for decision logic and integration tests for the full pipeline.

## Testing

### Unit Tests
```python
import pytest
from your_agent import YourAgent

@pytest.mark.asyncio
async def test_agent_decision():
    agent = YourAgent(agent_id="test")
    await agent.start()

    # Send test intelligence
    await agent.receive_intelligence(test_message)

    # Verify decision
    stats = agent.get_stats()
    assert stats["total_decisions"] == 1

    await agent.stop()
```

### Integration Tests
See `tests/integration/test_agent_pipeline.py` for examples.

## Performance Considerations

1. **Async Processing**: Agents process intelligence asynchronously
2. **Queue Management**: Intelligence is queued for processing
3. **Memory Efficiency**: Old decisions are automatically cleaned up
4. **Context Limits**: Keep context size reasonable

## Future Enhancements

- Multi-agent coordination
- Reinforcement learning integration
- Advanced decision strategies
- Portfolio management
- Risk management frameworks
- Backtesting capabilities

## Example Agents

- **PriceMonitorAgent**: Monitors prices and generates alerts
- **TradingAgent**: Makes buy/sell decisions (to be implemented)
- **RiskAgent**: Manages portfolio risk (to be implemented)
- **SentimentAgent**: Analyzes news sentiment (to be implemented)

## Support

For questions or issues with the Agents Framework, refer to the main CIAL documentation.
