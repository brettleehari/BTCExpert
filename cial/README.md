# CIAL - Crypto Intelligence Abstraction Layer

**Tagline**: "The Neural Network for Crypto Data Intelligence"

## Overview

CIAL is an agentic crypto platform with intelligent data abstraction that enables AI agents to make sophisticated trading decisions. It abstracts the chaos of crypto markets into structured intelligence streams that AI agents can consume.

## Architecture

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

## Quick Start

### 1. Clone and Setup

```bash
cd cial
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Infrastructure

```bash
# Start Docker services (Redis, Kafka, PostgreSQL)
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run CIAL

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json
- **Health Check**: http://localhost:8000/health

## Project Structure

```
cial/
├── core/                          # Core CIAL components
│   ├── intelligence_broker.py     # Central routing (Session 2)
│   ├── event_stream.py           # Real-time distribution (Session 4)
│   ├── validation_service.py     # Cross-validation (Session 8)
│   └── pattern_matcher.py        # AI pattern recognition
├── memory/
│   ├── short_term_memory.py      # Redis STM (Session 3)
│   ├── long_term_memory.py       # PostgreSQL LTM (Session 6)
│   ├── memory_manager.py         # Lifecycle management
│   └── agent_context.py          # Agent memory interface
├── connectors/
│   ├── price_intelligence/       # Price data (Session 5)
│   ├── sentiment_intelligence/   # Sentiment (Session 9)
│   └── onchain_intelligence/     # On-chain data
├── api/
│   ├── v1/
│   │   ├── intelligence.py       # Intelligence endpoints ✅
│   │   ├── agents.py            # Agent management ✅
│   │   ├── memory.py            # Memory endpoints ✅
│   │   └── validation.py        # Validation endpoints ✅
│   ├── models/                   # Pydantic models
│   └── middleware/               # Auth, rate limiting
├── infrastructure/
│   ├── config.py                 # Configuration ✅
│   └── logging_config.py         # Logging setup ✅
├── tests/
│   ├── test_health.py            # Health tests ✅
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── load/                     # Load tests
├── main.py                       # FastAPI application ✅
├── docker-compose.yml            # Infrastructure ✅
├── requirements.txt              # Dependencies ✅
├── pytest.ini                    # Test configuration ✅
└── .env.example                  # Environment template ✅
```

## Current Status: Session 1 Complete ✅

### Completed Components

✅ **Project Foundation**
- Complete directory structure
- Docker Compose (Redis, Kafka, PostgreSQL, TimescaleDB)
- FastAPI application with health endpoints
- Configuration management with Pydantic Settings
- Structured logging with structlog
- pytest configuration
- API router skeletons for all endpoints

### API Endpoints (Placeholders)

**Intelligence API** (`/api/v1/intelligence`)
- `GET /stream/{stream_type}` - Intelligence streams
- `GET /price/{symbol}/current` - Current price
- `GET /sentiment/{symbol}/current` - Current sentiment

**Agents API** (`/api/v1/agents`)
- `POST /register` - Register agent
- `GET /{agent_id}/status` - Agent status
- `DELETE /{agent_id}` - Unregister agent

**Memory API** (`/api/v1/memory`)
- `GET /stm/{agent_id}/context` - STM context
- `POST /stm/{agent_id}/decision` - Store decision
- `GET /ltm/{agent_id}/patterns` - LTM patterns
- `POST /ltm/{agent_id}/learn` - Store learning

**Validation API** (`/api/v1/validation`)
- `GET /cross-check/{data_point}` - Cross-check data
- `GET /source-reliability` - Source reliability
- `GET /consensus/{topic}` - Consensus intelligence

## Development Roadmap

### Session 2: Intelligence Broker (Next)
- Agent registration and discovery
- Intelligence message routing
- Data normalization and validation
- Service registry

### Session 3: Short-Term Memory
- Redis-based STM system
- TTL-based data lifecycle
- Agent context management
- Real-time caching

### Session 4: Event Stream
- Kafka producer/consumer
- WebSocket real-time connections
- Stream topic management
- Agent subscriptions

### Session 5: CoinGecko Connector
- First data source integration
- Price intelligence pipeline
- Critical price alerts
- Complete data flow example

### Sessions 6-10
- Long-Term Memory (PostgreSQL + Vector DB)
- Base Agent Interface
- Intelligence Validation
- News Sentiment Connector
- Complete API Documentation

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m load
```

## Environment Variables

See `.env.example` for all configuration options. Key variables:

```bash
# Application
ENVIRONMENT=development
DEBUG=true
PORT=8000

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cial_ltm

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# External APIs
COINGECKO_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
```

## Infrastructure Services

### Redis (Port 6379)
- Short-Term Memory (STM)
- Agent context caching
- Real-time intelligence

### PostgreSQL (Port 5432)
- Long-Term Memory (LTM)
- Historical intelligence
- Vector similarity search (pgvector)

### Kafka (Port 9093)
- Event streaming
- Real-time intelligence distribution
- Agent subscriptions

### Kafka UI (Port 8080)
- Web interface for Kafka monitoring
- Topic management
- Message inspection

## Contributing

CIAL is built component-by-component following the 10-session development strategy. Each session adds a complete, testable component.

## License

MIT

## Support

For issues and questions, please refer to the documentation in `docs/architecture/`.

---

**Session 1 Status**: ✅ Complete
**Next Session**: Intelligence Broker Core
**Progress**: 1/10 sessions (10% complete)
