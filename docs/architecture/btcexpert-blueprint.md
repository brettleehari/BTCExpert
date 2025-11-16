# BTCExpert Implementation Blueprint

**Version**: 1.0.0
**Architecture**: LangGraph + PydanticAI Hybrid
**Status**: Recommended Stack

---

## System Overview

BTCExpert is an autonomous Bitcoin expert system that combines:
- **Adaptive learning** from AWS-BTC-Agent (EMA algorithms, exploration vs exploitation)
- **Multi-agent orchestration** from Trading Agent (14+ specialized agents)
- **State-of-the-art frameworks** (LangGraph + PydanticAI)
- **Production-grade reliability** (type safety, fault tolerance, observability)

---

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BTCExpert System                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           LangGraph Orchestration Layer              │   │
│  │                                                      │   │
│  │  StateGraph                                          │   │
│  │  ├── MarketAnalysis (parallel)                      │   │
│  │  ├── RiskAssessment (conditional)                   │   │
│  │  ├── StrategicDecision (sequential)                 │   │
│  │  ├── HumanApproval (checkpoint) [if high risk]     │   │
│  │  └── Execution (final)                              │   │
│  │                                                      │   │
│  │  Memory: In-thread + Cross-thread                    │   │
│  │  State: Persisted to PostgreSQL                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           PydanticAI Agent Layer                     │   │
│  │                                                      │   │
│  │  Agent[Context, Output] with:                        │   │
│  │  • Full type safety                                  │   │
│  │  • Durable execution                                 │   │
│  │  • Structured outputs                                │   │
│  │  • Tool orchestration                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Model Provider Layer                    │   │
│  │                                                      │   │
│  │  Dynamic Selection (AWS-BTC-Agent inspired):         │   │
│  │  • Simple tasks → Claude Haiku ($0.00025/1K)        │   │
│  │  • Analysis → Claude Sonnet ($0.003/1K)             │   │
│  │  • Critical → Claude Opus ($0.015/1K)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Market Hunter Agent

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

class MarketContext(BaseModel):
    """Input context for market analysis"""
    current_price: float
    price_change_24h: float
    volume_ratio: float
    timestamp: datetime
    market_regime: Literal["bull", "bear", "sideways"]
    volatility_level: Literal["low", "medium", "high"]

class MarketSignal(BaseModel):
    """Structured output from market analysis"""
    signal_type: Literal[
        "WHALE_ACTIVITY",
        "POSITIVE_NARRATIVE",
        "TECHNICAL_BREAKOUT",
        "INSTITUTIONAL_ACCUMULATION",
        "EXTREME_FUNDING",
        "ARBITRAGE_OPPORTUNITY"
    ]
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    source_quality: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    supporting_data: dict[str, Any]

class MarketHunterAgent:
    """
    Autonomous data source selection agent.
    Implements EMA learning algorithm from AWS-BTC-Agent.
    """

    def __init__(self, learning_rate: float = 0.1, exploration_rate: float = 0.2):
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        self.source_metrics: dict[str, SourceMetrics] = {}

        self.agent = Agent[MarketContext, list[MarketSignal]](
            model='anthropic:claude-sonnet-4-20250514',
            deps_type=MarketContext,
            output_type=list[MarketSignal],
            system_prompt="""You are an autonomous market intelligence agent.
            Analyze the provided market data and generate actionable signals.
            Focus on high-confidence opportunities with clear risk/reward profiles.""",
        )

    async def execute_cycle(self, context: MarketContext) -> list[MarketSignal]:
        # Select optimal data sources based on market conditions
        sources = self._select_sources(context)

        # Fetch data from selected sources
        data = await self._fetch_data(sources)

        # Run agent analysis
        result = await self.agent.run(context, tool_results=data)

        # Update source performance metrics (EMA learning)
        self._update_metrics(sources, result.data)

        return result.data

    def _select_sources(self, context: MarketContext) -> list[str]:
        """
        Intelligent source selection based on market conditions.
        High volatility → more sources (6)
        Low volatility → fewer sources (3)
        """
        num_sources = 6 if context.volatility_level == "high" else 4 if context.volatility_level == "medium" else 3

        # Balance exploitation vs exploration
        if random.random() < self.exploration_rate:
            # Explore: try underused sources
            return self._select_exploratory(num_sources)
        else:
            # Exploit: use best performing sources
            return self._select_best_performing(num_sources, context.market_regime)

    def _update_metrics(self, sources: list[str], signals: list[MarketSignal]):
        """
        EMA update: new_metric = (1 - α) × old + α × new
        """
        for source in sources:
            quality = self._calculate_quality(signals, source)
            old_metric = self.source_metrics[source].signal_quality
            new_metric = (1 - self.learning_rate) * old_metric + self.learning_rate * quality
            self.source_metrics[source].signal_quality = new_metric
```

### 2. Risk Manager Agent

```python
class PortfolioState(BaseModel):
    """Current portfolio state"""
    total_value: float
    cash_balance: float
    positions: dict[str, Position]
    risk_metrics: RiskMetrics
    max_position_size: float = 0.15  # 15% per asset
    min_cash_reserve: float = 0.10   # 10% cash reserve

class RiskAssessment(BaseModel):
    """Risk evaluation output"""
    risk_level: Literal["acceptable", "elevated", "high", "critical"]
    max_position_allowed: float
    stop_loss_price: float
    take_profit_price: float
    position_size_recommendation: float
    risk_reward_ratio: float
    warnings: list[str]
    approval_required: bool

class RiskManagerAgent:
    def __init__(self):
        self.agent = Agent[PortfolioState, RiskAssessment](
            model='anthropic:claude-sonnet-4-20250514',
            deps_type=PortfolioState,
            output_type=RiskAssessment,
            system_prompt="""You are a risk management agent.
            Evaluate portfolio risk and enforce position limits.
            Priority: Capital preservation > Growth > Optimization.""",
        )

    async def assess_trade(
        self,
        portfolio: PortfolioState,
        proposed_trade: TradeProposal
    ) -> RiskAssessment:
        # Inject proposed trade into context
        context = portfolio.model_copy(update={"proposed_trade": proposed_trade})

        result = await self.agent.run(context)

        # Flag for human approval if critical risk
        if result.data.risk_level == "critical":
            result.data.approval_required = True

        return result.data
```

### 3. Strategic Orchestrator Agent

```python
class StrategicContext(BaseModel):
    """Aggregated market and portfolio state"""
    market_signals: list[MarketSignal]
    portfolio_state: PortfolioState
    risk_assessment: RiskAssessment
    market_regime: str
    macro_indicators: dict[str, float]

class TradingDecision(BaseModel):
    """Final trading decision"""
    action: Literal["buy", "sell", "hold", "rebalance"]
    asset: str
    amount: float
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    execution_strategy: Literal["market", "limit", "dca", "twap"]
    urgency: Literal["immediate", "within_1h", "within_24h", "opportunistic"]

class StrategicOrchestratorAgent:
    def __init__(self):
        self.agent = Agent[StrategicContext, TradingDecision](
            model='anthropic:claude-sonnet-4-20250514',
            deps_type=StrategicContext,
            output_type=TradingDecision,
            system_prompt="""You are the strategic decision-making agent.
            Synthesize market signals, risk assessments, and portfolio state.
            Make high-conviction decisions with clear reasoning.
            Balance opportunity capture with risk management.""",
        )

    async def make_decision(self, context: StrategicContext) -> TradingDecision:
        return (await self.agent.run(context)).data
```

---

## LangGraph Workflow

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

class TradingWorkflowState(TypedDict):
    """Shared state across workflow nodes"""
    market_context: MarketContext
    market_signals: list[MarketSignal]
    portfolio_state: PortfolioState
    risk_assessment: Optional[RiskAssessment]
    trading_decision: Optional[TradingDecision]
    execution_result: Optional[ExecutionResult]
    requires_approval: bool
    approved: Optional[bool]

def create_trading_workflow() -> StateGraph:
    """Create LangGraph workflow for BTCExpert"""

    workflow = StateGraph(TradingWorkflowState)

    # Define nodes (each wraps a PydanticAI agent)
    workflow.add_node("analyze_market", analyze_market_node)
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("make_decision", make_decision_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("execute_trade", execute_trade_node)
    workflow.add_node("log_results", log_results_node)

    # Define edges (workflow logic)
    workflow.set_entry_point("analyze_market")

    workflow.add_edge("analyze_market", "assess_risk")
    workflow.add_edge("assess_risk", "make_decision")

    # Conditional edge: route to human approval if required
    workflow.add_conditional_edges(
        "make_decision",
        should_require_approval,
        {
            "needs_approval": "human_approval",
            "auto_execute": "execute_trade",
            "hold": END
        }
    )

    workflow.add_edge("human_approval", "execute_trade")
    workflow.add_edge("execute_trade", "log_results")
    workflow.add_edge("log_results", END)

    # Add memory for state persistence
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)

async def analyze_market_node(state: TradingWorkflowState) -> TradingWorkflowState:
    """Parallel data collection and signal generation"""
    market_hunter = MarketHunterAgent()
    signals = await market_hunter.execute_cycle(state["market_context"])

    return {**state, "market_signals": signals}

async def assess_risk_node(state: TradingWorkflowState) -> TradingWorkflowState:
    """Risk evaluation with position limits"""
    risk_manager = RiskManagerAgent()
    assessment = await risk_manager.assess_trade(
        state["portfolio_state"],
        state.get("proposed_trade")
    )

    return {
        **state,
        "risk_assessment": assessment,
        "requires_approval": assessment.approval_required
    }

def should_require_approval(state: TradingWorkflowState) -> str:
    """Route based on decision and risk"""
    if state["trading_decision"].action == "hold":
        return "hold"
    if state["requires_approval"]:
        return "needs_approval"
    return "auto_execute"
```

---

## Dynamic LLM Cost Optimization

```python
class ModelRouter:
    """
    Dynamic model selection for cost optimization.
    Implements AWS-BTC-Agent's 80-95% cost reduction strategy.
    """

    MODELS = {
        "haiku": {
            "id": "anthropic:claude-3-haiku-20240307",
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "capabilities": ["extraction", "simple_classification"]
        },
        "sonnet": {
            "id": "anthropic:claude-sonnet-4-20250514",
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "capabilities": ["analysis", "pattern_recognition", "reasoning"]
        },
        "opus": {
            "id": "anthropic:claude-3-opus-20240229",
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "capabilities": ["critical_decisions", "complex_reasoning"]
        }
    }

    def select_model(self, task_complexity: str) -> str:
        """
        Select optimal model based on task requirements.

        Examples:
        - "extraction" → Haiku (cheap, fast)
        - "analysis" → Sonnet (balanced)
        - "critical_decision" → Opus (most capable)
        """
        if task_complexity in ["extraction", "simple_classification", "data_formatting"]:
            return self.MODELS["haiku"]["id"]
        elif task_complexity in ["analysis", "pattern_recognition", "risk_assessment"]:
            return self.MODELS["sonnet"]["id"]
        elif task_complexity in ["critical_decision", "strategic_planning", "complex_reasoning"]:
            return self.MODELS["opus"]["id"]
        else:
            return self.MODELS["sonnet"]["id"]  # Default to balanced option

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for a model invocation"""
        for model_config in self.MODELS.values():
            if model_config["id"] == model:
                return (
                    (input_tokens / 1000) * model_config["cost_per_1k_input"] +
                    (output_tokens / 1000) * model_config["cost_per_1k_output"]
                )
        return 0.0
```

---

## Project Structure

```
BTCExpert/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── market_hunter.py      # MarketHunterAgent
│   │   ├── risk_manager.py       # RiskManagerAgent
│   │   ├── strategic_orchestrator.py
│   │   ├── execution_agent.py
│   │   └── models/
│   │       ├── context.py        # Pydantic input models
│   │       └── outputs.py        # Pydantic output models
│   │
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── trading_workflow.py   # LangGraph StateGraph
│   │   ├── nodes.py              # Workflow node implementations
│   │   └── conditions.py         # Conditional routing logic
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── market_data.py        # CoinGecko, Alpha Vantage
│   │   ├── sentiment.py          # NewsAPI, Twitter
│   │   ├── on_chain.py           # Blockchain analysis
│   │   ├── technical.py          # 60+ indicators
│   │   └── mcp_connectors.py     # MCP integrations
│   │
│   ├── learning/
│   │   ├── __init__.py
│   │   ├── ema_optimizer.py      # Adaptive learning
│   │   ├── source_metrics.py     # Performance tracking
│   │   └── model_router.py       # Dynamic LLM selection
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── repository.py         # Data access layer
│   │   └── migrations/
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app
│   │   ├── routes/
│   │   └── websockets.py         # Real-time updates
│   │
│   └── monitoring/
│       ├── __init__.py
│       ├── langsmith.py          # Tracing setup
│       ├── logfire.py            # Pydantic Logfire
│       └── metrics.py            # Custom metrics
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── config/
│   ├── settings.py               # Pydantic Settings
│   ├── models.yaml               # Model configurations
│   └── sources.yaml              # Data source configs
│
├── docs/
│   ├── architecture/
│   ├── research/
│   └── api/
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── pyproject.toml                # Poetry/PDM config
├── requirements.txt
└── README.md
```

---

## Dependencies

```toml
[project]
name = "btcexpert"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    # Core Frameworks
    "langgraph>=0.2.0",
    "pydantic-ai>=1.18.0",
    "pydantic>=2.5.0",

    # AI Models
    "anthropic>=0.40.0",
    "openai>=1.50.0",

    # Web Framework
    "fastapi>=0.110.0",
    "uvicorn>=0.30.0",

    # Database
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",

    # Caching
    "redis>=5.0.0",

    # Market Data
    "aiohttp>=3.9.0",
    "websockets>=12.0",

    # Technical Analysis
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "ta-lib>=0.4.28",

    # Observability
    "langsmith>=0.1.0",
    "logfire>=0.50.0",
    "prometheus-client>=0.19.0",

    # Utilities
    "python-dotenv>=1.0.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "mypy>=1.8.0",
    "ruff>=0.3.0",
    "hypothesis>=6.99.0",
]
```

---

## Next Steps

1. **Initialize project structure** with Poetry/PDM
2. **Set up LangGraph StateGraph** for trading workflow
3. **Implement PydanticAI agents** with type-safe interfaces
4. **Integrate adaptive learning** from AWS-BTC-Agent
5. **Configure observability** (LangSmith + Logfire)
6. **Build API layer** with FastAPI
7. **Implement data source connectors**
8. **Deploy with Docker + monitoring**

This blueprint provides a concrete, production-ready architecture that combines the best insights from AWS-BTC-Agent (adaptive learning, cost optimization) with state-of-the-art frameworks (LangGraph, PydanticAI) for a truly autonomous Bitcoin expert system.
