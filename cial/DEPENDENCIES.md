# Dependency & Version Management

**Last Updated:** 2025-12-13

This document explains how CIAL manages Python dependencies, Docker images, and version compatibility.

---

## Table of Contents

1. [Python Version](#python-version)
2. [Dependency Management Strategy](#dependency-management-strategy)
3. [Docker Image Versions](#docker-image-versions)
4. [Compatibility Matrix](#compatibility-matrix)
5. [Security & Updates](#security--updates)
6. [Development Workflow](#development-workflow)

---

## Python Version

### Supported Python Versions

**Primary:** Python **3.11.6**
**Compatible:** Python 3.11.x, 3.12.x

### Version Specification Files

| File | Purpose |
|------|---------|
| `.python-version` | pyenv/asdf version pinning |
| `pyproject.toml` | Package metadata (requires-python >= 3.11, < 3.13) |
| `Dockerfile` | Production image (python:3.11.6-slim-bookworm) |
| `Dockerfile.dev` | Development image (python:3.11.6-slim-bookworm) |

### Why Python 3.11?

- **Performance:** 10-60% faster than Python 3.10
- **Better error messages:** Enhanced tracebacks
- **Type hints:** Improved typing features
- **Stability:** LTS support until 2027
- **Library compatibility:** Best ecosystem support

---

## Dependency Management Strategy

### Philosophy: Pinned Versions for Stability

We use **exact version pinning** (e.g., `fastapi==0.115.0`) instead of flexible versions (e.g., `fastapi>=0.115.0`) because:

✅ **Reproducible builds** - Same versions every time
✅ **Avoid breaking changes** - No surprise updates
✅ **Security control** - Explicit upgrade decisions
✅ **Testing confidence** - Test exact prod versions

### Dependency Files

| File | Purpose | When to Use |
|------|---------|-------------|
| `requirements.txt` | Production dependencies | Production deployment |
| `requirements-dev.txt` | Development dependencies | Local development, CI/CD |
| `pyproject.toml` | Package metadata & tooling | Modern Python packaging |

### Key Dependencies by Category

#### Core Framework
```python
fastapi==0.115.0          # Web framework
uvicorn[standard]==0.32.0 # ASGI server
pydantic==2.9.0           # Data validation
pydantic-settings==2.5.0  # Settings management
```

#### Database & Storage
```python
# PostgreSQL
asyncpg==0.29.0          # Async PostgreSQL driver
psycopg2-binary==2.9.9   # Sync PostgreSQL driver
sqlalchemy==2.0.34       # ORM
alembic==1.13.0          # Database migrations
pgvector==0.3.0          # Vector similarity search

# Redis
redis==5.0.0             # Redis client
aiocache==0.12.2         # Async caching framework

# TimescaleDB
timescaledb==0.5.2       # Time-series database client
```

#### Message Queue
```python
aiokafka==0.11.0         # Async Kafka client
kafka-python==2.0.2      # Sync Kafka client
```

#### Security
```python
python-jose[cryptography]==3.3.0  # JWT tokens
passlib[bcrypt]==1.7.4            # Password hashing
slowapi==0.1.9                    # Rate limiting
```

#### Observability
```python
structlog==24.1.0         # Structured logging
prometheus-client==0.20.0 # Metrics
sentry-sdk==2.14.0        # Error tracking
```

#### Testing
```python
pytest==8.3.0             # Test framework
pytest-asyncio==0.24.0    # Async testing
pytest-cov==5.0.0         # Coverage
fakeredis==2.24.0         # Redis mocking
```

---

## Docker Image Versions

### All Docker Images Are Pinned!

We use **specific version tags** instead of `latest` to prevent breaking changes.

### Service Versions (docker-compose.yml)

| Service | Image | Version | Rationale |
|---------|-------|---------|-----------|
| **CIAL App** | Custom build | Python 3.11.6 | Application stability |
| **PostgreSQL** | pgvector/pgvector | pg16-v0.7.4 | Vector search support |
| **Redis** | redis | 7.2.4-alpine | Latest stable 7.x |
| **Kafka** | confluentinc/cp-kafka | 7.6.0 | Latest stable Confluent |
| **Zookeeper** | confluentinc/cp-zookeeper | 7.6.0 | Matches Kafka version |
| **TimescaleDB** | timescale/timescaledb | 2.14.2-pg16 | Time-series optimized |
| **Kafka UI** | provectuslabs/kafka-ui | v0.7.2 | Monitoring tool |
| **Prometheus** | prom/prometheus | v2.51.0 | Metrics collection |
| **Grafana** | grafana/grafana | 10.4.1 | Visualization |

### Version Update Policy

**Minor Updates:** Monthly (security patches)
**Major Updates:** Quarterly (after testing)
**Breaking Changes:** Planned migrations only

---

## Compatibility Matrix

### Python & Library Compatibility

| Python Version | FastAPI | Pydantic | SQLAlchemy | Redis | Status |
|----------------|---------|----------|------------|-------|--------|
| 3.11.6 ✅ | 0.115.0 | 2.9.0 | 2.0.34 | 5.0.0 | **Supported** |
| 3.12.x ⚠️ | 0.115.0 | 2.9.0 | 2.0.34 | 5.0.0 | Compatible |
| 3.10.x ❌ | 0.115.0 | 2.9.0 | 2.0.34 | 5.0.0 | Not recommended |

### Database Compatibility

| PostgreSQL | pgvector | TimescaleDB | CIAL Support |
|------------|----------|-------------|--------------|
| 16.x ✅ | 0.7.4 | 2.14.2 | **Supported** |
| 15.x ⚠️ | 0.7.x | 2.13.x | Compatible |
| 14.x ❌ | N/A | N/A | Not supported |

### Redis Compatibility

| Redis Version | CIAL Support | Notes |
|---------------|--------------|-------|
| 7.2.x ✅ | **Supported** | Recommended |
| 7.0.x ⚠️ | Compatible | Older stable |
| 6.x ❌ | Not supported | Missing features |

### Kafka Compatibility

| Kafka Version | Confluent | CIAL Support |
|---------------|-----------|--------------|
| 7.6.0 ✅ | cp-kafka:7.6.0 | **Supported** |
| 7.5.x ⚠️ | cp-kafka:7.5.x | Compatible |
| 3.x ❌ | N/A | Not supported |

---

## Security & Updates

### Automated Security Scanning

**Dependabot:** Enabled (GitHub)
- Checks for security vulnerabilities daily
- Creates automatic PRs for patch updates
- Scans Python dependencies and Docker images

**Tools:**
```bash
# Check for security vulnerabilities
pip install safety
safety check -r requirements.txt

# Check for outdated packages
pip list --outdated

# Audit Python dependencies
pip-audit
```

### Update Workflow

1. **Weekly:** Review Dependabot PRs for security patches
2. **Monthly:** Minor version updates (test in dev first)
3. **Quarterly:** Major version updates (planned migration)

### Security Best Practices

✅ Pin exact versions in `requirements.txt`
✅ Use official Docker images only
✅ Scan for vulnerabilities with `safety`
✅ Keep Python 3.11.x up to date with patches
✅ Review changelogs before upgrading
✅ Test upgrades in dev environment first

---

## Development Workflow

### Local Development Setup

```bash
# 1. Install Python 3.11.6
pyenv install 3.11.6
pyenv local 3.11.6

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements-dev.txt

# 4. Verify installation
python --version  # Should show 3.11.6
pip list
```

### Docker Development

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# With hot-reload enabled
# Code changes automatically reload the server
```

### Production Deployment

```bash
# Build production image
docker build -t cial:latest .

# Or use docker-compose
docker-compose up -d

# With monitoring (optional)
docker-compose --profile monitoring up -d
```

### Updating Dependencies

#### Update Single Package

```bash
# 1. Update in requirements.txt
vim requirements.txt
# Change: fastapi==0.115.0
# To:     fastapi==0.116.0

# 2. Rebuild virtual environment
pip install -r requirements.txt --upgrade

# 3. Test changes
pytest

# 4. Update lock file (if using pip-tools)
pip-compile requirements.in
```

#### Update All Packages (Careful!)

```bash
# NOT RECOMMENDED for production
# Only for major version migrations

# 1. Generate updated requirements
pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs pip install -U

# 2. Freeze new versions
pip freeze > requirements.txt

# 3. Extensive testing required!
pytest
```

### Testing Dependency Compatibility

```bash
# Run full test suite
pytest -v --cov

# Test specific integrations
pytest tests/integration/

# Load testing
locust -f tests/load/locustfile.py
```

---

## Troubleshooting

### Common Issues

#### Issue: `ModuleNotFoundError`

**Cause:** Missing dependency
**Solution:**
```bash
pip install -r requirements.txt
```

#### Issue: Version conflict

**Cause:** Incompatible package versions
**Solution:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### Issue: Docker build fails

**Cause:** Cached layer issues
**Solution:**
```bash
docker-compose build --no-cache
```

#### Issue: `ImportError` after upgrade

**Cause:** Breaking API changes
**Solution:**
1. Check package changelog
2. Update import statements
3. Review migration guide

---

## Version Upgrade Checklist

Before upgrading any dependency:

- [ ] Read changelog and release notes
- [ ] Check for breaking changes
- [ ] Update in `requirements.txt`
- [ ] Rebuild virtual environment
- [ ] Run full test suite (`pytest`)
- [ ] Test in dev environment
- [ ] Review compatibility matrix
- [ ] Update `DEPENDENCIES.md` (this file)
- [ ] Create PR with upgrade details
- [ ] Deploy to staging first
- [ ] Monitor for issues
- [ ] Deploy to production

---

## References

- [Python Release Schedule](https://devguide.python.org/versions/)
- [FastAPI Releases](https://github.com/tiangolo/fastapi/releases)
- [Pydantic V2 Migration](https://docs.pydantic.dev/latest/migration/)
- [Docker Official Images](https://hub.docker.com/_/python)
- [PostgreSQL Supported Versions](https://www.postgresql.org/support/versioning/)

---

**Maintained by:** CIAL Team  
**Last Review:** 2025-12-13  
**Next Review:** 2026-03-13 (Quarterly)
