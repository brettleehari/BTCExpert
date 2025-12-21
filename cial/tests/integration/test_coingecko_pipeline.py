"""
Integration tests for CoinGecko → CIAL pipeline
Tests the complete data flow: CoinGecko → Connector → Broker → Classification → STM → Agents
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.models.intelligence import IntelligenceImportance, IntelligenceType
from main import app

client = TestClient(app)


@pytest.fixture
def mock_coingecko_api():
    """Mock CoinGecko API responses"""
    return {
        "bitcoin": {
            "usd": 62500.0,
            "usd_24h_change": 2.5,
            "usd_24h_vol": 28500000000,
            "usd_market_cap": 1220000000000,
            "last_updated_at": 1234567890,
        },
        "ethereum": {
            "usd": 3200.0,
            "usd_24h_change": 1.8,
            "usd_24h_vol": 15000000000,
            "usd_market_cap": 385000000000,
            "last_updated_at": 1234567890,
        },
        "solana": {
            "usd": 145.0,
            "usd_24h_change": -0.5,
            "usd_24h_vol": 2500000000,
            "usd_market_cap": 65000000000,
            "last_updated_at": 1234567890,
        },
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_pipeline_live_price(mock_coingecko_api):
    """
    Test complete pipeline: CoinGecko → Broker → Classification → STM → Agents

    Pipeline stages:
    1. Fetch from CoinGecko API
    2. Create PriceIntelligence model
    3. Process through Intelligence Broker
    4. Validate and enrich
    5. Classify importance
    6. Cache in Short-Term Memory
    7. Route to interested agents
    """
    # First, register an agent interested in BTC price intelligence
    agent_data = {
        "agent_id": "btc_trading_agent",
        "agent_type": "trading",
        "capabilities": {
            "intelligence_types": ["price"],
            "symbols": ["BTC"],
            "min_importance": "normal",
            "real_time": True,
        },
    }
    register_response = client.post("/api/v1/agents/register", json=agent_data)
    assert register_response.status_code == 200

    # Mock the CoinGecko API call
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bitcoin": mock_coingecko_api["bitcoin"]}
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        # Fetch live price - this triggers the complete pipeline
        response = client.get("/api/v1/intelligence/price/BTC/live")
        assert response.status_code == 200

        data = response.json()

        # Verify intelligence message structure
        assert data["type"] == "price"
        assert data["source"] == "coingecko"
        assert data["symbol"] == "BTC"
        assert "id" in data
        assert "timestamp" in data
        assert data["validated"] is True

        # Verify price data
        assert data["data"]["current_price"] == 62500.0
        assert data["data"]["price_change_percentage_24h"] == 2.5
        assert data["data"]["volume_24h"] == 28500000000

        # Verify classification
        assert "importance" in data
        assert data["importance"] in ["CRITICAL", "NORMAL", "LOW"]

    # Verify the price was cached in STM
    stm_response = client.get("/api/v1/memory/stm/price/BTC")
    assert stm_response.status_code == 200
    stm_data = stm_response.json()
    assert stm_data["current_price"] == 62500.0

    # Verify the intelligence can be retrieved from cache
    cached_response = client.get("/api/v1/intelligence/price/BTC/current")
    assert cached_response.status_code == 200
    cached_data = cached_response.json()
    assert cached_data["data"]["current_price"] == 62500.0

    # Verify agent received the intelligence (check agent stats)
    agent_response = client.get("/api/v1/agents/btc_trading_agent/status")
    assert agent_response.status_code == 200
    agent_stats = agent_response.json()
    assert agent_stats["message_count"] >= 1  # Agent should have received at least one message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_price_fetch(mock_coingecko_api):
    """Test batch price fetching and caching"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_api
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        # Fetch batch prices
        symbols = ["BTC", "ETH", "SOL"]
        response = client.post("/api/v1/intelligence/price/batch", json=symbols)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert "prices" in data

        prices = data["prices"]
        assert "BTC" in prices
        assert "ETH" in prices
        assert "SOL" in prices

        # Verify price values
        assert prices["BTC"]["current_price"] == 62500.0
        assert prices["ETH"]["current_price"] == 3200.0
        assert prices["SOL"]["current_price"] == 145.0


@pytest.mark.integration
def test_connector_health_monitoring():
    """Test connector health status in service registry"""
    # Get connector list
    response = client.get("/api/v1/intelligence/connectors")
    assert response.status_code == 200

    data = response.json()
    connectors = data["connectors"]

    # Find CoinGecko connector
    coingecko = next((c for c in connectors if c["connector_id"] == "coingecko"), None)
    assert coingecko is not None
    assert coingecko["name"] == "CoinGecko Price API"
    assert IntelligenceType.PRICE.value in coingecko["intelligence_types"]

    # Get health status
    health_response = client.get("/api/v1/intelligence/connectors/coingecko/health")
    assert health_response.status_code == 200

    health = health_response.json()
    assert "status" in health
    assert "reliability_score" in health
    assert "total_requests" in health


@pytest.mark.integration
@pytest.mark.asyncio
async def test_price_change_classification():
    """
    Test that large price changes trigger CRITICAL importance classification
    """
    # Mock a large price change
    large_change_response = {
        "bitcoin": {
            "usd": 62500.0,
            "usd_24h_change": 15.0,  # Large change should trigger CRITICAL
            "usd_24h_vol": 28500000000,
            "usd_market_cap": 1220000000000,
        }
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_change_response
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        response = client.get("/api/v1/intelligence/price/BTC/live")
        assert response.status_code == 200

        data = response.json()
        assert data["importance"] == "CRITICAL"  # Large price change


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_filtering_by_symbol():
    """Test that agents only receive intelligence for their registered symbols"""
    # Register BTC-only agent
    btc_agent = {
        "agent_id": "btc_only_agent",
        "agent_type": "trading",
        "capabilities": {
            "intelligence_types": ["price"],
            "symbols": ["BTC"],
            "min_importance": "normal",
        },
    }
    client.post("/api/v1/agents/register", json=btc_agent)

    # Register ETH-only agent
    eth_agent = {
        "agent_id": "eth_only_agent",
        "agent_type": "trading",
        "capabilities": {
            "intelligence_types": ["price"],
            "symbols": ["ETH"],
            "min_importance": "normal",
        },
    }
    client.post("/api/v1/agents/register", json=eth_agent)

    # Fetch BTC price
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bitcoin": {
                "usd": 62500.0,
                "usd_24h_change": 2.5,
                "usd_24h_vol": 28500000000,
                "usd_market_cap": 1220000000000,
            }
        }
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        client.get("/api/v1/intelligence/price/BTC/live")

    # Check BTC agent received the message
    btc_agent_status = client.get("/api/v1/agents/btc_only_agent/status")
    assert btc_agent_status.json()["message_count"] >= 1

    # Check ETH agent did NOT receive the message (symbol mismatch)
    eth_agent_status = client.get("/api/v1/agents/eth_only_agent/status")
    assert eth_agent_status.json()["message_count"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_error_handling():
    """Test handling of CoinGecko API errors"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        response = client.get("/api/v1/intelligence/price/BTC/live")
        assert response.status_code == 500
        assert "Failed to fetch live price" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limiting():
    """Test that rate limiting is enforced"""
    import time

    from connectors.price_intelligence.coingecko_connector import get_coingecko_connector

    connector = get_coingecko_connector()

    # Make two requests in quick succession
    start = time.time()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bitcoin": {"usd": 62500.0, "usd_24h_change": 2.5}}
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        await connector.get_price("BTC")
        await connector.get_price("BTC")  # Second request should wait

    duration = time.time() - start

    # Second request should have been rate limited
    # Total time should be >= min_request_interval
    assert duration >= connector._min_request_interval - 0.1


@pytest.mark.integration
def test_intelligence_stream_includes_coingecko():
    """Test that CoinGecko intelligence appears in stream"""
    # First ingest some price intelligence
    intel_data = {
        "intelligence_type": "price",
        "source": "coingecko",
        "data": {
            "current_price": 62500.0,
            "price_change_percentage_24h": 2.5,
            "volume_24h": 28500000000,
            "market_cap": 1220000000000,
        },
        "symbol": "BTC",
    }
    client.post("/api/v1/intelligence/ingest", json=intel_data)

    # Get the price stream
    response = client.get("/api/v1/intelligence/stream/price?symbol=BTC")
    assert response.status_code == 200

    data = response.json()
    assert data["stream_type"] == "price"
    assert data["total"] >= 1

    # Find CoinGecko message
    coingecko_msgs = [m for m in data["messages"] if m["source"] == "coingecko"]
    assert len(coingecko_msgs) >= 1


@pytest.mark.integration
def test_stm_cache_stats_includes_prices():
    """Test that STM stats show cached price intelligence"""
    # Ingest some price data
    intel_data = {
        "intelligence_type": "price",
        "source": "coingecko",
        "data": {"current_price": 62500.0},
        "symbol": "BTC",
    }
    client.post("/api/v1/intelligence/ingest", json=intel_data)

    # Check STM stats
    response = client.get("/api/v1/memory/stm/stats")
    assert response.status_code == 200

    stats = response.json()
    assert "total_keys" in stats
    assert "intelligence_cached" in stats
    assert stats["intelligence_cached"] >= 1
