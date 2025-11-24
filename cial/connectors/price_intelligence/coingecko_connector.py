"""
CoinGecko Price Intelligence Connector
First data source integration with complete intelligence pipeline
"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from api.models.intelligence import IntelligenceType, PriceIntelligence
from core.intelligence_broker import get_intelligence_broker
from core.service_registry import get_service_registry
from infrastructure.config import settings
from infrastructure.logging_config import logger


class CoinGeckoConnector:
    """
    CoinGecko API connector for price intelligence.

    Features:
    - Real-time price data
    - 24h price changes
    - Volume and market cap
    - Rate limiting (50 requests/minute free tier)
    - Error handling and retry logic
    - Automatic intelligence pipeline integration
    """

    BASE_URL = "https://api.coingecko.com/api/v3"
    CONNECTOR_ID = "coingecko"

    def __init__(self):
        self.broker = get_intelligence_broker()
        self.service_registry = get_service_registry()
        self.api_key = settings.COINGECKO_API_KEY

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.2  # 50 requests/minute = 1.2s between requests

        logger.info("CoinGeckoConnector initialized")

    async def get_price(self, symbol: str) -> Optional[PriceIntelligence]:
        """
        Get current price intelligence for a cryptocurrency.

        Args:
            symbol: Cryptocurrency symbol (BTC, ETH, etc.)

        Returns:
            Optional[PriceIntelligence]: Price data or None if failed
        """
        try:
            # Map symbol to CoinGecko ID
            coin_id = self._symbol_to_id(symbol)

            # Rate limiting
            await self._wait_for_rate_limit()

            # Fetch from CoinGecko
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/simple/price"
                params = {
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_last_updated_at": "true"
                }

                if self.api_key:
                    params["x_cg_pro_api_key"] = self.api_key

                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()

                data = response.json()

                if coin_id not in data:
                    logger.warning(f"No data returned for {symbol} ({coin_id})")
                    return None

                coin_data = data[coin_id]

                # Create PriceIntelligence model
                price_intel = PriceIntelligence(
                    symbol=symbol.upper(),
                    current_price=coin_data["usd"],
                    price_change_24h=coin_data.get("usd_24h_change", 0),
                    price_change_percentage_24h=coin_data.get("usd_24h_change", 0),
                    volume_24h=coin_data.get("usd_24h_vol", 0),
                    market_cap=coin_data.get("usd_market_cap", 0)
                )

                # Report success to service registry
                self.service_registry.report_success(self.CONNECTOR_ID)

                logger.info(
                    f"Fetched price for {symbol}",
                    price=price_intel.current_price,
                    change_24h=price_intel.price_change_percentage_24h
                )

                return price_intel

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {symbol}: {e.response.status_code}")
            self.service_registry.report_error(self.CONNECTOR_ID, str(e))
            return None

        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}", exc_info=True)
            self.service_registry.report_error(self.CONNECTOR_ID, str(e))
            return None

    async def get_prices_batch(self, symbols: List[str]) -> Dict[str, PriceIntelligence]:
        """
        Get prices for multiple cryptocurrencies in batch.

        Args:
            symbols: List of cryptocurrency symbols

        Returns:
            Dict[str, PriceIntelligence]: Symbol -> Price data mapping
        """
        try:
            # Map symbols to CoinGecko IDs
            coin_ids = [self._symbol_to_id(s) for s in symbols]
            ids_str = ",".join(coin_ids)

            await self._wait_for_rate_limit()

            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/simple/price"
                params = {
                    "ids": ids_str,
                    "vs_currencies": "usd",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true",
                    "include_market_cap": "true"
                }

                if self.api_key:
                    params["x_cg_pro_api_key"] = self.api_key

                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()

                data = response.json()

                results = {}
                for symbol, coin_id in zip(symbols, coin_ids):
                    if coin_id in data:
                        coin_data = data[coin_id]
                        results[symbol.upper()] = PriceIntelligence(
                            symbol=symbol.upper(),
                            current_price=coin_data["usd"],
                            price_change_24h=coin_data.get("usd_24h_change", 0),
                            price_change_percentage_24h=coin_data.get("usd_24h_change", 0),
                            volume_24h=coin_data.get("usd_24h_vol", 0),
                            market_cap=coin_data.get("usd_market_cap", 0)
                        )

                self.service_registry.report_success(self.CONNECTOR_ID)

                logger.info(f"Fetched batch prices for {len(results)} symbols")

                return results

        except Exception as e:
            logger.error(f"Failed to fetch batch prices: {e}", exc_info=True)
            self.service_registry.report_error(self.CONNECTOR_ID, str(e))
            return {}

    async def ingest_price_intelligence(self, symbol: str) -> bool:
        """
        Fetch price and ingest into CIAL intelligence pipeline.

        This demonstrates the complete data flow:
        CoinGecko → Connector → Intelligence Broker → Classification → Routing → STM → Agents

        Args:
            symbol: Cryptocurrency symbol

        Returns:
            bool: True if successfully ingested
        """
        price_intel = await self.get_price(symbol)

        if not price_intel:
            return False

        # Ingest into intelligence broker
        message = self.broker.process_intelligence(
            intelligence_type=IntelligenceType.PRICE,
            source=self.CONNECTOR_ID,
            data=price_intel.model_dump(),
            symbol=symbol.upper(),
            metadata={
                "connector": self.CONNECTOR_ID,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(
            f"Price intelligence ingested: {symbol}",
            message_id=message.id,
            importance=message.importance.value
        )

        return True

    def _symbol_to_id(self, symbol: str) -> str:
        """Map common symbols to CoinGecko IDs."""
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
            "BNB": "binancecoin",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "DOT": "polkadot",
            "MATIC": "matic-network"
        }

        return symbol_map.get(symbol.upper(), symbol.lower())

    async def _wait_for_rate_limit(self):
        """Implement rate limiting to stay within API limits."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()


# Global connector instance
_coingecko_connector: Optional[CoinGeckoConnector] = None


def get_coingecko_connector() -> CoinGeckoConnector:
    """Get the global CoinGecko connector instance."""
    global _coingecko_connector
    if _coingecko_connector is None:
        _coingecko_connector = CoinGeckoConnector()
    return _coingecko_connector
