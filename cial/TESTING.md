# CIAL Testing Guide

Comprehensive testing guide for the Crypto Intelligence Abstraction Layer.

## 🧪 Testing Strategy

CIAL uses a multi-layered testing approach:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test complete workflows and pipelines
3. **Load Tests**: Test system under stress (future)

## 📦 Test Structure

```
tests/
├── unit/                          # Unit tests
│   ├── test_agent_registry.py     # Agent registry tests
│   ├── test_intelligence_broker.py # Broker tests
│   ├── test_short_term_memory.py  # STM tests
│   ├── test_kafka_manager.py      # Kafka tests
│   ├── test_coingecko_connector.py # Connector tests
│   └── test_base_agent.py         # Agent framework tests
├── integration/                    # Integration tests
│   ├── test_api_endpoints.py      # API endpoint tests
│   ├── test_stm_api.py           # STM API tests
│   ├── test_coingecko_pipeline.py # CoinGecko pipeline tests
│   ├── test_kafka_pipeline.py     # Kafka pipeline tests
│   └── test_agent_pipeline.py     # Agent pipeline tests
└── conftest.py                    # Shared fixtures
```

## 🚀 Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_base_agent.py -v

# Specific test function
pytest tests/unit/test_base_agent.py::test_agent_initialization -v
```

### Test Markers

```bash
# Run slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Run integration tests
pytest -m integration

# Run asyncio tests
pytest -m asyncio
```

## 📝 Writing Tests

### Unit Test Example

```python
import pytest
from unittest.mock import Mock, patch

def test_agent_initialization():
    """Test that agent initializes correctly."""
    agent = MyAgent("test_agent")

    assert agent.agent_id == "test_agent"
    assert agent.status == AgentStatus.INITIALIZING


@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await my_async_function()
    assert result is not None
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_pipeline():
    """Test complete intelligence pipeline."""
    # Setup
    agent = TestAgent("integration_agent")
    await agent.start()

    # Execute
    intelligence = create_test_intelligence()
    await broker.process_intelligence(intelligence)

    # Verify
    assert agent.received_intelligence
    await agent.stop()
```

### Mocking External Services

```python
@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    with patch('redis.Redis') as mock:
        yield mock

@pytest.fixture
def mock_http_response():
    """Mock HTTP API response."""
    with patch('httpx.AsyncClient') as mock:
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock.get.return_value = mock_response
        yield mock
```

## 🔍 Test Coverage

### Current Coverage

- **Overall Coverage**: ~85%
- **Core Services**: 90%+
- **API Endpoints**: 80%+
- **Infrastructure**: 85%+
- **Agents**: 80%+

### Coverage Report

```bash
# Generate coverage report
pytest --cov=. --cov-report=term-missing

# HTML coverage report
pytest --cov=. --cov-report=html
```

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Core | 90% | 92% |
| API | 85% | 83% |
| Infrastructure | 85% | 87% |
| Agents | 80% | 81% |
| Connectors | 80% | 85% |
| Validation | 85% | 88% |

## 🐛 Debugging Tests

### Verbose Output

```bash
# Show print statements
pytest -s

# Show detailed info
pytest -vv

# Show locals on failure
pytest -l
```

### Failed Test Debugging

```bash
# Run only failed tests
pytest --lf

# Run failed tests first
pytest --ff

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb
```

### Logging During Tests

```python
import logging

def test_with_logging(caplog):
    """Test with captured logs."""
    with caplog.at_level(logging.INFO):
        my_function()
        assert "Expected log message" in caplog.text
```

## 🔧 Test Fixtures

### Common Fixtures

```python
@pytest.fixture
def test_agent():
    """Create test agent."""
    agent = TestAgent("test_001")
    yield agent
    # Cleanup
    asyncio.run(agent.stop())

@pytest.fixture
def sample_intelligence():
    """Create sample intelligence message."""
    return IntelligenceMessage(
        id="test_001",
        type=IntelligenceType.PRICE,
        importance=IntelligenceImportance.NORMAL,
        source="test",
        data={"current_price": 62500.0},
        timestamp=datetime.utcnow(),
        validated=True
    )

@pytest.fixture
async def running_services():
    """Start all required services."""
    # Setup
    await redis_manager.connect()
    await kafka_manager.connect()
    await postgres_manager.connect()

    yield

    # Teardown
    await redis_manager.disconnect()
    await kafka_manager.disconnect()
    await postgres_manager.disconnect()
```

## 📊 Performance Testing

### Load Test Example

```python
import time

@pytest.mark.slow
def test_high_volume_intelligence():
    """Test system under high load."""
    start = time.time()

    # Process 1000 intelligence messages
    for i in range(1000):
        broker.process_intelligence(create_intelligence(i))

    duration = time.time() - start
    assert duration < 10.0  # Should complete in 10 seconds
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory_profiler

# Run with memory profiling
pytest --memprof
```

## 🔐 Testing External APIs

### Mocking CoinGecko

```python
@pytest.fixture
def mock_coingecko():
    """Mock CoinGecko API responses."""
    with patch('httpx.AsyncClient') as mock:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bitcoin": {
                "usd": 62500.0,
                "usd_24h_change": 2.5
            }
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = Mock()
        mock.return_value = mock_client
        yield mock
```

### Testing Rate Limiting

```python
@pytest.mark.asyncio
async def test_rate_limiting():
    """Test that rate limiting works."""
    connector = CoinGeckoConnector()

    start = time.time()
    await connector.get_price("BTC")
    await connector.get_price("BTC")  # Should wait
    duration = time.time() - start

    assert duration >= connector._min_request_interval
```

## 🎯 Testing Best Practices

### 1. Test Isolation

```python
# Good: Each test is independent
def test_feature_a():
    setup_a()
    test_a()
    teardown_a()

def test_feature_b():
    setup_b()
    test_b()
    teardown_b()
```

### 2. Clear Test Names

```python
# Good: Descriptive test name
def test_agent_receives_price_intelligence_and_makes_buy_decision():
    pass

# Bad: Vague test name
def test_agent():
    pass
```

### 3. AAA Pattern (Arrange, Act, Assert)

```python
def test_intelligence_broker_routes_to_correct_agents():
    # Arrange
    broker = IntelligenceBroker()
    agent = TestAgent("test")
    broker.agent_registry.register_agent(agent)

    # Act
    message = create_intelligence("BTC")
    broker.process_intelligence(message)

    # Assert
    assert agent.received_intelligence
```

### 4. Mock External Dependencies

```python
# Good: Mock external services
@patch('connectors.coingecko_connector.httpx.AsyncClient')
def test_price_fetch(mock_client):
    # Test without actual API call
    pass
```

### 5. Test Edge Cases

```python
def test_agent_handles_missing_price_data():
    """Test agent handles missing data gracefully."""
    message = IntelligenceMessage(data={})  # No price
    result = agent.process(message)
    assert result is None  # Should not crash
```

## 🚨 Common Issues

### Async Test Failures

```python
# Problem: Forgot @pytest.mark.asyncio
async def test_my_async_function():
    result = await my_function()
    assert result

# Solution: Add marker
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_function()
    assert result
```

### Mock Not Working

```python
# Problem: Wrong import path
@patch('my_module.external_function')  # Wrong path

# Solution: Patch where it's used
@patch('my_module.internal.external_function')  # Correct
```

### Flaky Tests

```python
# Problem: Race condition with async
@pytest.mark.asyncio
async def test_flaky():
    await start_something()
    assert something_is_done()  # May fail

# Solution: Add proper waiting
@pytest.mark.asyncio
async def test_stable():
    await start_something()
    await asyncio.sleep(0.1)  # Give time to complete
    assert something_is_done()
```

## 📈 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## 🎓 Test Examples

### Complete Test File Example

```python
"""
Tests for Intelligence Broker
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from core.intelligence_broker import IntelligenceBroker
from api.models.intelligence import IntelligenceType, IntelligenceImportance


@pytest.fixture
def broker():
    """Create broker instance with mocked dependencies."""
    with patch('core.intelligence_broker.get_agent_registry'), \
         patch('core.intelligence_broker.get_short_term_memory'), \
         patch('core.intelligence_broker.get_long_term_memory'):
        broker = IntelligenceBroker()
        yield broker


def test_broker_initialization(broker):
    """Test broker initializes correctly."""
    assert broker is not None
    assert broker.agent_registry is not None


@pytest.mark.asyncio
async def test_process_intelligence(broker):
    """Test intelligence processing pipeline."""
    message = broker.process_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        source="test",
        data={"current_price": 62500.0},
        symbol="BTC"
    )

    assert message.id is not None
    assert message.validated is True
    assert message.type == IntelligenceType.PRICE


def test_classify_critical_price_change(broker):
    """Test critical classification for large price changes."""
    message = Mock()
    message.type = IntelligenceType.PRICE
    message.data = {"price_change_percentage_24h": 15.0}

    classified = broker._classify_importance(message)

    assert classified.importance == IntelligenceImportance.CRITICAL
```

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## 💡 Quick Commands

```bash
# Quick test run
pytest -v --tb=short

# Test with coverage
pytest --cov=. --cov-report=term-missing

# Test specific module
pytest tests/unit/test_base_agent.py -v

# Debug failed test
pytest --lf --pdb

# Performance profile
pytest --profile

# Generate HTML report
pytest --html=report.html
```

---

**For issues with tests, check**: https://github.com/brettleehari/BTCExpert/issues
