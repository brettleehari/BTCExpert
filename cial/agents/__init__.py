"""
CIAL Agents Framework

Base framework for building intelligent crypto agents that consume
intelligence from CIAL and make autonomous decisions.

Key Components:
- BaseAgent: Abstract base class for all agents
- AgentDecision: Standardized decision representation
- AgentDecisionType: Types of decisions agents can make

Sample Implementations:
- PriceMonitorAgent: Price monitoring and alerting

Usage:
```python
from agents.base_agent import BaseAgent, AgentDecision, AgentDecisionType
from agents.sample_price_monitor_agent import PriceMonitorAgent

# Create and start an agent
agent = PriceMonitorAgent(
    agent_id="btc_monitor",
    symbols=["BTC", "ETH"],
    alert_threshold=5.0
)

await agent.start()

# Send intelligence to agent
await agent.receive_intelligence(intelligence_message)

# Get agent stats
stats = agent.get_stats()

# Stop agent
await agent.stop()
```
"""

from .base_agent import AgentDecision, AgentDecisionType, BaseAgent
from .sample_price_monitor_agent import PriceMonitorAgent

__all__ = ["BaseAgent", "AgentDecision", "AgentDecisionType", "PriceMonitorAgent"]
