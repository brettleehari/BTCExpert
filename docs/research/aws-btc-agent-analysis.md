# AWS-BTC-Agent: Autonomous Bitcoin Market Intelligence System

## Project Overview

The AWS-BTC-Agent is an **autonomous Bitcoin market intelligence agent** built on Amazon Bedrock AgentCore that revolutionizes how trading systems access and process real-time market data. Unlike traditional bots that query fixed data sources, this agent **independently decides** which data sources to query based on real-time market conditions, learned performance patterns, and adaptive algorithms.

## Core Intelligence: Autonomous Decision Making

The Market Hunter Agent is a truly agentic system that:
- Autonomously decides which of 8 data sources to query each cycle
- Learns from experience using adaptive algorithms
- Adapts to market conditions (volatility, trend, time of day)
- Generates signals for other trading agents
- Self-optimizes through exploration vs exploitation

### Key Differentiators

- **Intelligent Source Selection**: Chooses 3-6 optimal data sources per cycle from 8 available options
- **Market-Adaptive**: Behavior changes based on volatility, trend direction, and trading sessions
- **Learning Algorithm**: Uses exponential moving average to learn which sources perform best
- **Dynamic LLM Routing**: Automatically selects from 10 Bedrock models for cost optimization
- **Self-Optimization**: Balances exploration vs exploitation to discover new patterns

## 8 Autonomous Data Sources

The agent independently selects from:

1. **Whale Movements** - Large on-chain transactions (>100 BTC)
2. **Narrative Shifts** - Social media trends and sentiment
3. **Arbitrage Opportunities** - Cross-exchange price spreads
4. **Influencer Signals** - Technical analysis from traders
5. **Technical Breakouts** - Chart pattern detection
6. **Institutional Flows** - Large holder movements
7. **Derivatives Signals** - Funding rates, liquidations
8. **Macro Signals** - Fear & Greed Index, market sentiment

### Smart Selection Logic

- **High Volatility (>5%)**: Queries 6 sources for comprehensive analysis
- **Low Volatility (<2%)**: Queries 3 sources for efficiency
- **Bullish Markets**: Prioritizes institutional/influencer signals
- **Bearish Markets**: Focuses on derivatives/whale movement data
- **Trading Sessions**: Optimizes based on Asian/European/American market hours

## Revolutionary LLM Cost Optimization

Dynamic model selection across 10 Bedrock models:

### Supported Models
- Claude 3 (Haiku/Sonnet/3.5 Sonnet/Opus)
- Titan (Express/Lite)
- Llama 3 (8B/70B)
- Mistral (7B/Large)

### Cost Optimization Examples

| Task Type | Model | Cost per 1K tokens |
|-----------|-------|-------------------|
| Simple Extraction | Claude 3 Haiku | $0.00025 |
| Pattern Recognition | Claude 3.5 Sonnet | $0.003 |
| Critical Decisions | Claude 3 Opus | $0.015 |

**Real Cost Impact:**
- Fixed Model (always Sonnet): $27.30
- Dynamic Routing: $20.01 → **26.7% savings**
- **Yearly Savings: $3,830+ for 24/7 operation**
- **Overall: 80-95% cost reduction vs. fixed model approach**

## Adaptive Learning Algorithm

Uses exponential moving average algorithm:
```
new_metric = (1 - α) × old_metric + α × new_observation
```

- **Learning Rate (α)**: 0.1 (10% weight to new data)
- **Exploration Rate**: 0.2 (20% chance to try underused sources)

### Performance Metrics Tracked

- **Success Rate**: How often each source provides actionable data
- **Signal Quality**: Accuracy of predictions from each source
- **Efficiency**: Speed and reliability of data retrieval
- **Market Condition Performance**: Which sources work best in specific market states

## Signal Generation & Integration

Generated signals for other agents:

| Signal Type | Description | Severity |
|------------|-------------|----------|
| WHALE_ACTIVITY | Large transactions detected | High |
| POSITIVE_NARRATIVE | Bullish trending topics | Medium |
| INSTITUTIONAL_ACCUMULATION | Large holdings increase | High |
| EXTREME_FUNDING | High funding rates | Critical |
| EXTREME_FEAR/GREED | Sentiment extremes | Medium |

### Integration Points

- **Trading Agents**: Provides market intelligence for decision making
- **Risk Management**: Alerts for extreme market conditions
- **Portfolio Optimization**: Data for rebalancing and position sizing
- **Content Creation**: Market insights for social media automation

## Enterprise Architecture

```
Market Hunter Agent (Amazon Bedrock Agent)
├── Agent Core (Claude 3 Sonnet)
│   ├── Market Context Assessment
│   ├── Source Selection Logic
│   ├── Result Analysis
│   └── Signal Generation
│
├── Action Group (Lambda)
│   ├── query_whale_movements()
│   ├── query_narrative_shifts()
│   ├── query_arbitrage_opportunities()
│   ├── query_influencer_signals()
│   ├── query_technical_breakouts()
│   ├── query_institutional_flows()
│   ├── query_derivatives_signals()
│   └── query_macro_signals()
│
├── Knowledge Base (Optional)
│   ├── Historical Market Data
│   ├── Trading Patterns
│   └── Market Indicators
│
└── Storage (PostgreSQL)
    ├── agent_executions
    ├── source_metrics_history
    ├── system_alerts
    └── [8 data source tables]
```

## Production Deployment

### Requirements
- **AWS Account** with Bedrock access
- **Python 3.9+** runtime environment
- **PostgreSQL** database for persistence
- **AWS Lambda** for action group functions

### Monthly Operating Costs

| Service | Cost Range |
|---------|-----------|
| Bedrock Agent | ~$50-100 |
| Claude 3 Sonnet | ~$0.003/1K input, ~$0.015/1K output |
| Lambda Functions | ~$5-10 (1M invocations free tier) |
| PostgreSQL RDS | ~$15-50 (db.t3.micro or Aurora Serverless) |
| **Total Estimated** | **$70-160/month** |

## Usage Examples

### Basic Implementation

```python
from market_hunter_agent import MarketHunterAgent

# Initialize agent
agent = MarketHunterAgent(
    bedrock_agent_id="YOUR_AGENT_ID",
    bedrock_agent_alias_id="YOUR_ALIAS_ID",
    region_name="us-east-1",
    learning_rate=0.1,
    exploration_rate=0.2
)

# Execute one cycle
market_data = {
    'price': 62500,
    'price_change_24h_percent': 4.2,
    'volume_ratio': 1.2
}
result = agent.execute_cycle(market_data)
```

### 24/7 Production Loop

```python
import schedule

def run_agent_cycle():
    market_data = fetch_current_market_data()
    result = agent.execute_cycle(market_data)
    db.store_execution(result)
    process_signals(result['signals'])

# Run every 10 minutes
schedule.every(10).minutes.do(run_agent_cycle)

while True:
    schedule.run_pending()
    time.sleep(1)
```

## Performance Analytics

### Real-time Monitoring

```python
report = agent.get_performance_report()
for source, metrics in report['source_performance'].items():
    print(f"{source}:")
    print(f"  Success Rate: {metrics['success_rate']:.3f}")
    print(f"  Signal Quality: {metrics['signal_quality']:.3f}")
    print(f"  Efficiency: {metrics['efficiency']:.3f}")
```

### Database Analytics

```sql
-- Top performing sources
SELECT source_name, AVG(signal_quality) as avg_quality
FROM source_metrics_history
GROUP BY source_name
ORDER BY avg_quality DESC;

-- Agent performance over time
SELECT DATE(timestamp) as date, COUNT(*) as cycles,
       AVG(signals_count) as avg_signals
FROM agent_executions
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

## Use Cases & Integration

### Perfect For
- **Trading System Intelligence Layer**: Provides smart data sourcing for trading algorithms
- **Risk Management Systems**: Early warning signals for extreme market conditions
- **Portfolio Optimization**: Market intelligence for rebalancing decisions
- **Research & Backtesting**: Historical pattern analysis and source effectiveness
- **Cost-Conscious Operations**: Dramatic reduction in LLM costs while maintaining quality

### Integration Scenarios
- **Feed into TweetBot**: Market intelligence for social media content
- **Enhance TradingAgents**: Replace static data sources with intelligent selection
- **Standalone Intelligence**: Pure market intelligence service for other systems
- **Enterprise Dashboard**: Real-time market intelligence for trading desks

## Future Roadmap

Planned enhancements:
- **Meta-learning**: Optimize learning rate automatically
- **Multi-objective optimization**: Accuracy vs cost balancing
- **Causal inference**: Determine if signals caused agent actions
- **Collaborative filtering**: Learn from other agents
- **Anomaly detection**: Auto-detect unusual patterns
- **Natural language explanations**: Explain decisions in plain English

## Key Advantages

1. **Solves Real-time Data Bottleneck**: Intelligently selects optimal data sources
2. **Dramatic Cost Reduction**: 80-95% savings through dynamic LLM routing
3. **Continuously Learning**: Adapts performance based on market conditions
4. **Enterprise Ready**: AWS infrastructure, PostgreSQL persistence, production monitoring
5. **Integration Friendly**: Clean APIs for connecting to trading systems
6. **Transparent Performance**: Comprehensive analytics and explainable decisions

---

## Key Insights for BTCExpert Implementation

### Core Architecture Patterns to Adopt

1. **Adaptive Source Selection** - Don't query all data sources; intelligently select based on market conditions
2. **EMA Learning Algorithm** - Track performance metrics to improve over time
3. **Cost-Optimized LLM Routing** - Match model capability to task complexity
4. **Signal-Based Communication** - Generate typed signals for inter-agent communication
5. **Exploration vs Exploitation** - Balance proven strategies with discovering new patterns

### Implementation Priorities

1. **Phase 1**: Core adaptive learning infrastructure
2. **Phase 2**: Multi-source data integration with intelligent selection
3. **Phase 3**: Dynamic LLM cost optimization
4. **Phase 4**: Signal generation and agent coordination
5. **Phase 5**: Performance analytics and self-optimization

### Critical Success Factors

- **Real-time adaptability** over static rule-based systems
- **Cost efficiency** without sacrificing decision quality
- **Transparent metrics** for continuous improvement
- **Modular architecture** for easy integration with other agents
