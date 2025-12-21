"""
Unit tests for CoinGecko Connector
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from api.models.intelligence import IntelligenceType, PriceIntelligence
from connectors.price_intelligence.coingecko_connector import CoinGeckoConnector


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies for CoinGeckoConnector"""
    with (
        patch(
            "connectors.price_intelligence.coingecko_connector.get_intelligence_broker"
        ) as mock_broker,
        patch(
            "connectors.price_intelligence.coingecko_connector.get_service_registry"
        ) as mock_registry,
        patch("connectors.price_intelligence.coingecko_connector.settings") as mock_settings,
    ):

        mock_settings.COINGECKO_API_KEY = None

        yield {
            "broker": mock_broker.return_value,
            "registry": mock_registry.return_value,
            "settings": mock_settings,
        }


@pytest.fixture
def connector(mock_dependencies):
    """Create CoinGeckoConnector instance with mocked dependencies"""
    return CoinGeckoConnector()


@pytest.fixture
def sample_coingecko_response():
    """Sample response from CoinGecko API"""
    return {
        "bitcoin": {
            "usd": 62500.0,
            "usd_24h_change": 2.5,
            "usd_24h_vol": 28500000000,
            "usd_market_cap": 1220000000000,
            "last_updated_at": 1234567890,
        }
    }


@pytest.mark.asyncio
async def test_get_price_success(connector, mock_dependencies, sample_coingecko_response):
    """Test successful price fetch"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_coingecko_response
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await connector.get_price("BTC")

        assert result is not None
        assert isinstance(result, PriceIntelligence)
        assert result.symbol == "BTC"
        assert result.current_price == 62500.0
        assert result.price_change_percentage_24h == 2.5
        assert result.volume_24h == 28500000000
        assert result.market_cap == 1220000000000

        # Verify service registry was called
        mock_dependencies["registry"].report_success.assert_called_once_with("coingecko")


@pytest.mark.asyncio
async def test_get_price_http_error(connector, mock_dependencies):
    """Test handling of HTTP errors"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limited", request=Mock(), response=mock_response
        )

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await connector.get_price("BTC")

        assert result is None
        mock_dependencies["registry"].report_error.assert_called_once()


@pytest.mark.asyncio
async def test_get_price_no_data(connector, mock_dependencies):
    """Test handling when no data is returned for symbol"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Empty response
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await connector.get_price("INVALID")

        assert result is None


@pytest.mark.asyncio
async def test_get_prices_batch_success(connector, mock_dependencies):
    """Test batch price fetching"""
    batch_response = {
        "bitcoin": {
            "usd": 62500.0,
            "usd_24h_change": 2.5,
            "usd_24h_vol": 28500000000,
            "usd_market_cap": 1220000000000,
        },
        "ethereum": {
            "usd": 3200.0,
            "usd_24h_change": 1.8,
            "usd_24h_vol": 15000000000,
            "usd_market_cap": 385000000000,
        },
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = batch_response
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        symbols = ["BTC", "ETH"]
        results = await connector.get_prices_batch(symbols)

        assert len(results) == 2
        assert "BTC" in results
        assert "ETH" in results
        assert results["BTC"].current_price == 62500.0
        assert results["ETH"].current_price == 3200.0

        mock_dependencies["registry"].report_success.assert_called_once()


@pytest.mark.asyncio
async def test_get_prices_batch_error(connector, mock_dependencies):
    """Test batch price fetch error handling"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        results = await connector.get_prices_batch(["BTC", "ETH"])

        assert results == {}
        mock_dependencies["registry"].report_error.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_price_intelligence_success(
    connector, mock_dependencies, sample_coingecko_response
):
    """Test complete intelligence ingestion pipeline"""
    mock_message = Mock()
    mock_message.id = "msg_001"
    mock_message.importance.value = "NORMAL"
    mock_dependencies["broker"].process_intelligence.return_value = mock_message

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_coingecko_response
        mock_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await connector.ingest_price_intelligence("BTC")

        assert result is True

        # Verify broker was called to process intelligence
        mock_dependencies["broker"].process_intelligence.assert_called_once()
        call_args = mock_dependencies["broker"].process_intelligence.call_args

        assert call_args.kwargs["intelligence_type"] == IntelligenceType.PRICE
        assert call_args.kwargs["source"] == "coingecko"
        assert call_args.kwargs["symbol"] == "BTC"
        assert "current_price" in call_args.kwargs["data"]


@pytest.mark.asyncio
async def test_ingest_price_intelligence_failure(connector, mock_dependencies):
    """Test ingestion failure when price fetch fails"""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("API error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await connector.ingest_price_intelligence("BTC")

        assert result is False
        mock_dependencies["broker"].process_intelligence.assert_not_called()


def test_symbol_to_id_mapping(connector):
    """Test symbol to CoinGecko ID mapping"""
    assert connector._symbol_to_id("BTC") == "bitcoin"
    assert connector._symbol_to_id("ETH") == "ethereum"
    assert connector._symbol_to_id("SOL") == "solana"
    assert connector._symbol_to_id("ADA") == "cardano"

    # Test unknown symbol (should return lowercase)
    assert connector._symbol_to_id("UNKNOWN") == "unknown"


@pytest.mark.asyncio
async def test_rate_limiting(connector):
    """Test rate limiting mechanism"""
    import time

    # First request should not wait
    start = time.time()
    await connector._wait_for_rate_limit()
    duration1 = time.time() - start
    assert duration1 < 0.1  # Should be instant

    # Second request immediately after should wait
    start = time.time()
    await connector._wait_for_rate_limit()
    duration2 = time.time() - start
    assert duration2 >= connector._min_request_interval - 0.1  # Allow small margin


@pytest.mark.asyncio
async def test_get_price_with_api_key(mock_dependencies):
    """Test price fetch with API key"""
    mock_dependencies["settings"].COINGECKO_API_KEY = "test_api_key"
    connector = CoinGeckoConnector()

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

        await connector.get_price("BTC")

        # Verify API key was included in request
        call_args = mock_client.get.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["x_cg_pro_api_key"] == "test_api_key"


def test_connector_initialization(mock_dependencies):
    """Test connector initialization"""
    connector = CoinGeckoConnector()

    assert connector.broker is not None
    assert connector.service_registry is not None
    assert connector.BASE_URL == "https://api.coingecko.com/api/v3"
    assert connector.CONNECTOR_ID == "coingecko"
    assert connector._min_request_interval == 1.2  # 50 requests/minute
