# Crypto Intelligence Abstraction Layer (CIAL) Architecture

## Project Overview

**Name**: **CIAL** (Crypto Intelligence Abstraction Layer)
**Tagline**: "The Neural Network for Crypto Data Intelligence"
**Goal**: Build an agentic crypto platform with intelligent data abstraction that enables AI agents to make sophisticated trading decisions
**Technology**: Python-based with FastAPI, Apache Kafka, Redis, and AI/ML integrations

---

## CIAL Core Concept

**CIAL** abstracts the chaos of crypto markets into structured intelligence streams that AI agents can consume. Think of it as the "nervous system" for crypto trading agents.

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENTIC LAYER (Northbound)                 │
│  Trading Agent | Risk Agent | Sentiment Agent | Portfolio   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  CIAL CORE (Intelligence)                    │
│  Intelligence Broker | STM | LTM | Event Stream | Validator │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                DATA CONNECTORS (Southbound)                  │
│  CoinGecko | NewsAPI | Twitter | WebSocket | OnChain | DEX  │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Components

### 1. Intelligence Broker (Core CIAL Component)
**Purpose**: Central intelligence routing and service discovery for crypto agents
**Technology**: FastAPI + Apache Kafka + Pydantic
**Responsibilities**:
- Agent registration and discovery
- Intelligence stream routing
- Data normalization and validation
- Cross-source intelligence fusion

### 2. Short-Term Memory (STM) - Real-time Intelligence
**Purpose**: Hot intelligence data for immediate agent consumption
**Technology**: Redis + TimescaleDB
**Data Persistence Strategy**:
```python
# HOT DATA (Redis - 1-24 hours retention)
- Live prices and orderbook
- Real-time sentiment scores
- Active whale movements
- Breaking news alerts
- Technical indicator signals
- Agent decision context
```

### 3. Long-Term Memory (LTM) - Historical Intelligence
**Purpose**: Pattern analysis and strategic intelligence
**Technology**: PostgreSQL + ClickHouse + Vector DB (ChromaDB)
**Data Persistence Strategy**:
```python
# COLD DATA (PostgreSQL/ClickHouse - Indefinite retention)
- Historical price patterns
- Seasonal sentiment trends
- Agent learning patterns
- Market regime classifications
- Portfolio performance history
- Regulatory event impacts
```

### 4. Event Stream - Real-time Intelligence Distribution
**Purpose**: Pub/sub intelligence distribution to agents
**Technology**: Apache Kafka + WebSocket
**Stream Categories**:
```python
INTELLIGENCE_STREAMS = {
    "price.critical": "Major price movements >5%",
    "sentiment.breaking": "Breaking news sentiment shifts",
    "whale.massive": "Large wallet movements >$10M",
    "technical.signals": "Strong technical indicator signals",
    "regulatory.alerts": "Regulatory announcement impacts",
    "defi.events": "DeFi protocol events and exploits"
}
```

---

## Data Intelligence Classification

### Intelligence Persistence Decision Matrix

| Data Type | Persistence | TTL | Storage | Reasoning |
|-----------|------------|-----|---------|-----------|
| **Live Prices** | STM | 24h | Redis | High frequency, loses value quickly |
| **Orderbook Depth** | STM | 1h | Redis | Very transient, only current state matters |
| **Breaking News** | STM→LTM | 30d→∞ | Redis→PG | Immediate impact, historical context |
| **Sentiment Scores** | STM+LTM | 24h+∞ | Redis+PG | Real-time + trend analysis |
| **Whale Movements** | STM+LTM | 7d+∞ | Redis+CH | Pattern recognition + immediate alerts |
| **Technical Indicators** | STM | 24h | Redis | Recalculated frequently |
| **Agent Decisions** | LTM | ∞ | PG+Vector | Learning and improvement |
| **Market Regimes** | LTM | ∞ | PG | Strategic pattern recognition |
| **Regulatory Events** | LTM | ∞ | PG | Long-term impact analysis |

### Intelligence Flow Pipeline

```python
class IntelligenceFlow:
    """
    Pipeline: RAW DATA → VALIDATION → ENRICHMENT → CLASSIFICATION → ROUTING
    """

    def process_intelligence(self, raw_data):
        validated = self.validate_source(raw_data)
        enriched = self.cross_reference(validated)
        classified = self.classify_importance(enriched)

        if classified.importance == "CRITICAL":
            self.route_to_stm(classified)        # Immediate agent access
            self.stream_to_agents(classified)    # Real-time notification
            self.persist_to_ltm(classified)      # Historical record
        elif classified.importance == "NORMAL":
            self.route_to_stm(classified)        # Cache for agents
            self.batch_to_ltm(classified)        # Batch persistence
        else:
            self.discard_or_sample(classified)   # Noise reduction
```

---

## CIAL API Specification

### Core Intelligence APIs

#### 1. Intelligence Stream API
```python
# Real-time intelligence consumption
GET /api/v1/intelligence/stream/{stream_type}
WebSocket /ws/intelligence/{agent_id}

# Examples:
GET /api/v1/intelligence/stream/price.critical
GET /api/v1/intelligence/stream/sentiment.breaking
```

#### 2. Agent Registration API
```python
POST /api/v1/agents/register
PUT /api/v1/agents/{agent_id}/capabilities
GET /api/v1/agents/{agent_id}/status
DELETE /api/v1/agents/{agent_id}
```

#### 3. Memory Management API
```python
# Short-term memory
GET /api/v1/memory/stm/{agent_id}/context
POST /api/v1/memory/stm/{agent_id}/decision
GET /api/v1/memory/stm/{agent_id}/market-state

# Long-term memory
GET /api/v1/memory/ltm/{agent_id}/patterns
POST /api/v1/memory/ltm/{agent_id}/learn
GET /api/v1/memory/ltm/{agent_id}/similar-scenarios
```

### Market Intelligence APIs

#### 4. Price Intelligence API
```python
GET /api/v1/intelligence/price/{symbol}/current
GET /api/v1/intelligence/price/{symbol}/history
GET /api/v1/intelligence/price/{symbol}/predictions
GET /api/v1/intelligence/price/alerts/massive-movements
```

#### 5. Sentiment Intelligence API
```python
GET /api/v1/intelligence/sentiment/{symbol}/current
GET /api/v1/intelligence/sentiment/{symbol}/trending
GET /api/v1/intelligence/sentiment/news/breaking
GET /api/v1/intelligence/sentiment/social/viral
```

#### 6. On-Chain Intelligence API
```python
GET /api/v1/intelligence/onchain/whale-movements
GET /api/v1/intelligence/onchain/exchange-flows
GET /api/v1/intelligence/onchain/defi-activity
GET /api/v1/intelligence/onchain/wallet/{address}/profile
```

### Agent Intelligence APIs

#### 7. Decision Support API
```python
POST /api/v1/intelligence/decision-support
GET /api/v1/intelligence/market-regime/current
GET /api/v1/intelligence/risk-assessment/{scenario}
GET /api/v1/intelligence/opportunity-scan/{criteria}
```

#### 8. Cross-Validation API
```python
GET /api/v1/intelligence/validation/cross-check/{data_point}
GET /api/v1/intelligence/validation/source-reliability
GET /api/v1/intelligence/validation/consensus/{topic}
```

---

## Complete Data Source Inventory & API Mapping

### Tier 1 - Critical Market Data
```python
TIER_1_SOURCES = {
    "coingecko": {
        "apis": ["price", "volume", "market_cap", "price_change"],
        "rate_limit": "50/minute",
        "reliability": 0.95,
        "cial_mapping": "/api/v1/intelligence/price"
    },
    "coinmarketcap": {
        "apis": ["price", "metadata", "quotes", "listings"],
        "rate_limit": "333/minute",
        "reliability": 0.97,
        "cial_mapping": "/api/v1/intelligence/price"
    },
    "binance_ws": {
        "apis": ["ticker", "depth", "trades", "klines"],
        "rate_limit": "unlimited_ws",
        "reliability": 0.99,
        "cial_mapping": "/api/v1/intelligence/price/realtime"
    }
}
```

### Tier 2 - Sentiment & News Intelligence
```python
TIER_2_SOURCES = {
    "newsapi": {
        "apis": ["everything", "top_headlines", "sources"],
        "rate_limit": "1000/day",
        "reliability": 0.85,
        "cial_mapping": "/api/v1/intelligence/sentiment/news"
    },
    "twitter_v2": {
        "apis": ["recent_search", "stream", "users", "tweets"],
        "rate_limit": "300/15min",
        "reliability": 0.80,
        "cial_mapping": "/api/v1/intelligence/sentiment/social"
    },
    "reddit_api": {
        "apis": ["subreddit", "comments", "search", "hot"],
        "rate_limit": "60/minute",
        "reliability": 0.75,
        "cial_mapping": "/api/v1/intelligence/sentiment/reddit"
    }
}
```

### Tier 3 - On-Chain Intelligence
```python
TIER_3_SOURCES = {
    "etherscan": {
        "apis": ["account", "transactions", "tokens", "stats"],
        "rate_limit": "5/second",
        "reliability": 0.99,
        "cial_mapping": "/api/v1/intelligence/onchain/ethereum"
    },
    "whale_alert": {
        "apis": ["transactions", "blockchain", "status"],
        "rate_limit": "custom",
        "reliability": 0.90,
        "cial_mapping": "/api/v1/intelligence/onchain/whale-movements"
    },
    "dexscreener": {
        "apis": ["tokens", "pairs", "search", "profiles"],
        "rate_limit": "300/minute",
        "reliability": 0.85,
        "cial_mapping": "/api/v1/intelligence/onchain/dex"
    }
}
```

---

## Development Strategy

### Phase 1: Foundation (Weeks 1-2)
- Core CIAL infrastructure
- Intelligence Broker skeleton
- Event Stream service with Kafka
- Basic FastAPI setup

### Phase 2: Memory Systems (Weeks 3-4)
- Short-Term Memory (Redis)
- Long-Term Memory (PostgreSQL + Vector DB)
- Memory Management APIs
- Data lifecycle automation

### Phase 3: Data Connectors (Weeks 5-6)
- CoinGecko connector
- Multi-source sentiment connectors
- On-chain intelligence connectors
- Rate limiting and error handling

### Phase 4: Agent Intelligence APIs (Weeks 7-8)
- Intelligence APIs with OpenAPI docs
- Decision support system
- Cross-validation service
- Agent authentication

### Phase 5: Advanced Features (Weeks 9-10)
- ML-powered pattern recognition
- Agent learning feedback loop
- Intelligence dashboard
- Monitoring and observability

---

## Project Structure

```
cial/
├── core/
│   ├── intelligence_broker.py        # Central intelligence routing
│   ├── event_stream.py              # Real-time distribution
│   ├── validation_service.py        # Cross-source validation
│   └── pattern_matcher.py           # AI pattern recognition
├── memory/
│   ├── short_term_memory.py         # Redis-based STM
│   ├── long_term_memory.py          # PostgreSQL + Vector LTM
│   ├── memory_manager.py            # Data lifecycle
│   └── agent_context.py             # Agent memory interface
├── connectors/
│   ├── price_intelligence/          # Price data connectors
│   ├── sentiment_intelligence/      # Sentiment connectors
│   └── onchain_intelligence/        # On-chain connectors
├── api/
│   ├── v1/
│   │   ├── intelligence/            # Core intelligence endpoints
│   │   ├── agents/                  # Agent management
│   │   ├── memory/                  # Memory management
│   │   └── validation/              # Cross-validation
│   ├── models/                      # Pydantic models
│   └── middleware/                  # Auth, rate limiting
├── infrastructure/
│   ├── kafka_setup.py              # Kafka configuration
│   ├── redis_config.py             # Redis configuration
│   ├── postgres_setup.py           # Database setup
│   └── monitoring.py               # System monitoring
└── tests/
    ├── unit/
    ├── integration/
    └── load/
```

---

## Success Metrics & Deliverables

### Primary Deliverable: Complete CIAL Platform
- **Intelligence APIs**: 25+ endpoints with full OpenAPI documentation
- **Agent Integration**: SDK for seamless agent development
- **Multi-Source Intelligence**: 15+ integrated data sources
- **Real-time Processing**: <100ms latency for critical intelligence
- **Scalable Architecture**: Support for 100+ concurrent agents

### Technical Deliverables
- [ ] CIAL Core Platform (Python/FastAPI)
- [ ] Complete API Documentation (Swagger/OpenAPI)
- [ ] Agent Development SDK
- [ ] Memory Management System (STM + LTM)
- [ ] Intelligence Validation Engine
- [ ] Real-time Event Streaming (Kafka)
- [ ] ML-Powered Analytics (Pattern Recognition)
- [ ] Production Deployment Scripts (Docker/K8s)
