# CIAL — Crypto Intelligence Abstraction Layer

**Enterprise-grade cryptocurrency intelligence platform with real-time data aggregation, AI-powered insights, and WebSocket streaming.**

CIAL collects market intelligence from multiple data sources, routes it through an intelligent broker system, and serves it via REST APIs and real-time WebSocket streams to client applications and AI agents.

## Architecture

```
 Client Applications (Dashboards, AI Agents, APIs)
              |  REST API       |  WebSocket
 FastAPI Application
   JWT Auth | Rate Limiting | Circuit Breakers
 Intelligence Broker
   Agent Registry | Data Routing | Caching
 Kafka | Redis | Postgres+pgvector | TimescaleDB
```

## Key Features

**Data Layer**
- PostgreSQL 16 with pgvector for semantic search across market data
- TimescaleDB for 100x faster historical time-series queries
- Redis 7 for multi-tier caching (96% faster response times)
- Kafka for event streaming and real-time data distribution

**Intelligence Engine**
- Agent Registry coordinating multiple AI agents for market analysis
- Dual memory system: Redis (short-term) + PostgreSQL (persistent)
- Intelligence Broker for routing and distribution

**API and Streaming**
- REST API with FastAPI + Pydantic V2 validation
- WebSocket streaming supporting 10,000+ concurrent connections
- JWT authentication and rate limiting

**Reliability**
- Circuit breakers (pybreaker) and retry logic (tenacity)
- Prometheus metrics + OpenTelemetry distributed tracing
- Structured logging (structlog) + Sentry error tracking

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Core** | Python 3.11.6, FastAPI, Uvicorn |
| **Data** | PostgreSQL 16, pgvector, TimescaleDB, Redis 7, Kafka |
| **Performance** | aiocache, asyncpg, multi-tier caching |
| **Security** | JWT (PyJWT), slowapi rate limiting |
| **Resilience** | pybreaker, tenacity |
| **Observability** | Prometheus, OpenTelemetry, structlog, Sentry |
| **Deployment** | Docker, Render.com, Railway, GCP Cloud Run |

## Quickstart

```bash
git clone https://github.com/brettleehari/BTCExpert.git
cd BTCExpert
docker-compose up -d
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## Author

**Hariprasad Sudharshan** - [GitHub](https://github.com/brettleehari)
