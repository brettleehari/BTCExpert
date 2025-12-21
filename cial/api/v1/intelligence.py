"""
CIAL Intelligence API Router
Endpoints for accessing market intelligence

Version: 1.0 (with versioned responses)
"""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Query, Request

from api.models.intelligence import (
    IntelligenceStreamResponse,
    IntelligenceType,
)
from api.models.responses import (
    APIVersion,
    success_response,
)
from connectors.price_intelligence.coingecko_connector import get_coingecko_connector
from core.intelligence_broker import get_intelligence_broker
from core.service_registry import get_service_registry
from infrastructure.logging_config import logger

router = APIRouter()


def _get_request_metadata(request: Request, start_time: float) -> dict[str, Any]:
    """Build metadata for API responses"""
    return {
        "request_id": str(uuid.uuid4()),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "path": str(request.url.path),
        "method": request.method,
    }


@router.get("/stream/{stream_type}", response_model=IntelligenceStreamResponse)
async def get_intelligence_stream(
    stream_type: str = Path(..., description="Intelligence stream type"),  # noqa: B008
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum messages to return"),  # noqa: B008
    symbol: str | None = Query(None, description="Filter by cryptocurrency symbol"),  # noqa: B008
):
    """
    Get intelligence stream data.

    Stream Types:
    - price: Price intelligence (CoinGecko, CMC, exchanges)
    - sentiment: News and social sentiment
    - whale: Large wallet movements
    - technical: Technical indicator signals
    - regulatory: Regulatory announcements
    - defi: DeFi protocol events
    - onchain: General on-chain activity

    Returns:
        IntelligenceStreamResponse: Intelligence messages from the stream
    """
    # Map stream_type string to enum
    try:
        intel_type = IntelligenceType(stream_type)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stream type: {stream_type}. Valid types: price, sentiment, whale, technical, regulatory, defi, onchain",
        ) from e

    broker = get_intelligence_broker()
    messages = broker.get_recent_intelligence(
        intelligence_type=intel_type, symbol=symbol, limit=limit
    )

    return IntelligenceStreamResponse(
        stream_type=stream_type,
        messages=messages,
        total=len(messages),
        has_more=len(messages) >= limit,
    )


@router.get("/price/{symbol}/current")
async def get_current_price(
    request: Request, symbol: str = Path(..., description="Cryptocurrency symbol (e.g., BTC, ETH)")  # noqa: B008
):
    """
    Get current price intelligence for a cryptocurrency.

    Returns the most recent cached price from STM.

    **Response Format (v1.0):**
    ```json
    {
        "version": "1.0",
        "status": "success",
        "data": {
            "id": "price_BTC_20240115_103000_abc123",
            "type": "price",
            "symbol": "BTC",
            "data": {"current_price": 45000.0, ...},
            ...
        },
        "metadata": {
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "xyz789",
            "processing_time_ms": 12.5
        }
    }
    ```

    Returns:
        VersionedResponse[IntelligenceMessage]: Versioned price intelligence
    """
    start_time = time.time()

    broker = get_intelligence_broker()
    messages = broker.get_recent_intelligence(
        intelligence_type=IntelligenceType.PRICE, symbol=symbol.upper(), limit=1
    )

    if not messages:
        raise HTTPException(
            status_code=404, detail=f"No price intelligence available for {symbol.upper()}"
        )

    metadata = _get_request_metadata(request, start_time)
    metadata["symbol"] = symbol.upper()
    metadata["source"] = messages[0].source

    return success_response(data=messages[0], version=APIVersion.V1, metadata=metadata)


@router.get("/price/{symbol}/live")
async def get_live_price(
    symbol: str = Path(..., description="Cryptocurrency symbol (e.g., BTC, ETH)")  # noqa: B008
):
    """
    Fetch live price from CoinGecko and ingest into CIAL pipeline.

    This endpoint:
    1. Fetches current price from CoinGecko
    2. Validates and enriches the data
    3. Classifies importance
    4. Caches in STM
    5. Routes to interested agents
    6. Returns the intelligence message

    Returns:
        IntelligenceMessage: Fresh price intelligence from CoinGecko
    """
    try:
        connector = get_coingecko_connector()
        success = await connector.ingest_price_intelligence(symbol)

        if not success:
            raise HTTPException(
                status_code=503, detail=f"Failed to fetch price for {symbol.upper()} from CoinGecko"
            )

        # Get the freshly cached price
        broker = get_intelligence_broker()
        messages = broker.get_recent_intelligence(
            intelligence_type=IntelligenceType.PRICE, symbol=symbol.upper(), limit=1
        )

        if not messages:
            raise HTTPException(status_code=500, detail="Price was fetched but not found in cache")

        return messages[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch live price: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch live price") from e


@router.post("/price/batch")
async def get_batch_prices(
    request: Request,
    symbols: list[str] = Body(  # noqa: B008
        ..., description="List of cryptocurrency symbols", example=["BTC", "ETH", "SOL"]
    ),
):
    """
    Fetch live prices for multiple cryptocurrencies in a single request.

    This is more efficient than making individual requests.

    **Response Format (v1.0):**
    ```json
    {
        "version": "1.0",
        "status": "success",
        "data": {
            "total": 3,
            "prices": {
                "BTC": {...},
                "ETH": {...},
                "SOL": {...}
            }
        },
        "metadata": {
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "xyz789",
            "symbols_requested": 3
        }
    }
    ```

    Returns:
        VersionedResponse: Batch price data
    """
    start_time = time.time()

    try:
        connector = get_coingecko_connector()
        prices = await connector.get_prices_batch(symbols)

        if not prices:
            raise HTTPException(
                status_code=503, detail="Failed to fetch batch prices from CoinGecko"
            )

        metadata = _get_request_metadata(request, start_time)
        metadata["symbols_requested"] = len(symbols)
        metadata["symbols_returned"] = len(prices)

        return success_response(
            data={"total": len(prices), "prices": prices}, version=APIVersion.V1, metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch batch prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch batch prices") from e


@router.get("/sentiment/{symbol}/current")
async def get_current_sentiment(symbol: str = Path(..., description="Cryptocurrency symbol")):  # noqa: B008
    """
    Get current sentiment intelligence for a cryptocurrency.

    Note: This endpoint will be fully implemented in Session 9 (News Sentiment Connector).
    Currently returns the most recent sentiment intelligence from the broker.

    Returns:
        IntelligenceMessage: Most recent sentiment intelligence
    """
    broker = get_intelligence_broker()
    messages = broker.get_recent_intelligence(
        intelligence_type=IntelligenceType.SENTIMENT, symbol=symbol.upper(), limit=1
    )

    if not messages:
        raise HTTPException(
            status_code=404, detail=f"No sentiment intelligence available for {symbol.upper()}"
        )

    return messages[0]


@router.post("/ingest")
async def ingest_intelligence(
    intelligence_type: IntelligenceType = Body(..., description="Type of intelligence"),  # noqa: B008
    source: str = Body(..., description="Data source identifier"),  # noqa: B008
    data: dict[str, Any] = Body(..., description="Intelligence data payload"),  # noqa: B008
    symbol: str | None = Body(None, description="Cryptocurrency symbol"),  # noqa: B008
    metadata: dict[str, Any] | None = Body(None, description="Additional metadata"),  # noqa: B008
):
    """
    Ingest raw intelligence data into CIAL pipeline.

    This endpoint allows data connectors to submit intelligence for processing.

    Pipeline: RAW DATA → VALIDATION → ENRICHMENT → CLASSIFICATION → ROUTING

    Returns:
        IntelligenceMessage: Processed intelligence message
    """
    try:
        broker = get_intelligence_broker()
        message = broker.process_intelligence(
            intelligence_type=intelligence_type,
            source=source,
            data=data,
            symbol=symbol,
            metadata=metadata,
        )

        return message

    except Exception as e:
        logger.error(f"Failed to ingest intelligence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process intelligence") from e


@router.get("/stats")
async def get_intelligence_stats(request: Request):
    """
    Get intelligence broker statistics.

    Returns comprehensive statistics about:
    - Total messages processed
    - Messages by type and importance
    - Routing statistics
    - Processing performance

    **Response Format (v1.0):**
    ```json
    {
        "version": "1.0",
        "status": "success",
        "data": {
            "total_messages": 1523,
            "by_type": {...},
            "by_importance": {...},
            "routing_stats": {...}
        },
        "metadata": {
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "xyz789"
        }
    }
    ```

    Returns:
        VersionedResponse: Broker statistics
    """
    start_time = time.time()

    broker = get_intelligence_broker()
    stats = broker.get_broker_stats()

    metadata = _get_request_metadata(request, start_time)

    return success_response(data=stats, version=APIVersion.V1, metadata=metadata)


@router.get("/connectors")
async def list_connectors(
    request: Request,
    intelligence_type: IntelligenceType | None = Query(  # noqa: B008
        None, description="Filter by intelligence type"
    ),
    enabled_only: bool = Query(True, description="Only show enabled connectors"),  # noqa: B008
):
    """
    List all registered data connectors.

    Returns information about available data sources:
    - Connector ID and type
    - Health status and reliability
    - Configuration details

    **Response Format (v1.0):**
    ```json
    {
        "version": "1.0",
        "status": "success",
        "data": {
            "total": 2,
            "connectors": [...]
        },
        "metadata": {
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "xyz789",
            "filtered_by_type": "price"
        }
    }
    ```

    Returns:
        VersionedResponse: List of data connectors
    """
    start_time = time.time()

    registry = get_service_registry()

    if intelligence_type:
        connectors = registry.get_connectors_by_type(intelligence_type)
    elif enabled_only:
        connectors = registry.get_enabled_connectors()
    else:
        connectors = registry.get_all_connectors()

    metadata = _get_request_metadata(request, start_time)
    metadata["total_connectors"] = len(connectors)
    metadata["enabled_only"] = enabled_only
    if intelligence_type:
        metadata["filtered_by_type"] = intelligence_type.value

    return success_response(
        data={"total": len(connectors), "connectors": connectors},
        version=APIVersion.V1,
        metadata=metadata,
    )


@router.get("/connectors/{connector_id}/health")
async def get_connector_health(connector_id: str):
    """
    Get health status for a specific data connector.

    Returns:
        DataConnectorHealth: Connector health information
    """
    registry = get_service_registry()
    health = registry.get_health_status(connector_id)

    if not health:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

    return health
