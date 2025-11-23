"""
CIAL Intelligence API Router
Endpoints for accessing market intelligence
"""

from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, Dict, Any

from api.models.intelligence import (
    IntelligenceMessage,
    IntelligenceStreamResponse,
    IntelligenceType,
    IntelligenceImportance,
    DataConnector
)
from core.intelligence_broker import get_intelligence_broker
from core.service_registry import get_service_registry
from infrastructure.logging_config import logger

router = APIRouter()


@router.get("/stream/{stream_type}", response_model=IntelligenceStreamResponse)
async def get_intelligence_stream(
    stream_type: str = Path(..., description="Intelligence stream type"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum messages to return"),
    symbol: Optional[str] = Query(None, description="Filter by cryptocurrency symbol")
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
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stream type: {stream_type}. Valid types: price, sentiment, whale, technical, regulatory, defi, onchain"
        )

    broker = get_intelligence_broker()
    messages = broker.get_recent_intelligence(
        intelligence_type=intel_type,
        symbol=symbol,
        limit=limit
    )

    return IntelligenceStreamResponse(
        stream_type=stream_type,
        messages=messages,
        total=len(messages),
        has_more=len(messages) >= limit
    )


@router.get("/price/{symbol}/current")
async def get_current_price(
    symbol: str = Path(..., description="Cryptocurrency symbol (e.g., BTC, ETH)")
):
    """
    Get current price intelligence for a cryptocurrency.

    Note: This endpoint will be fully implemented in Session 5 (CoinGecko Connector).
    Currently returns the most recent price intelligence from the broker.

    Returns:
        IntelligenceMessage: Most recent price intelligence
    """
    broker = get_intelligence_broker()
    messages = broker.get_recent_intelligence(
        intelligence_type=IntelligenceType.PRICE,
        symbol=symbol.upper(),
        limit=1
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail=f"No price intelligence available for {symbol.upper()}"
        )

    return messages[0]


@router.get("/sentiment/{symbol}/current")
async def get_current_sentiment(
    symbol: str = Path(..., description="Cryptocurrency symbol")
):
    """
    Get current sentiment intelligence for a cryptocurrency.

    Note: This endpoint will be fully implemented in Session 9 (News Sentiment Connector).
    Currently returns the most recent sentiment intelligence from the broker.

    Returns:
        IntelligenceMessage: Most recent sentiment intelligence
    """
    broker = get_intelligence_broker()
    messages = broker.get_recent_intelligence(
        intelligence_type=IntelligenceType.SENTIMENT,
        symbol=symbol.upper(),
        limit=1
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail=f"No sentiment intelligence available for {symbol.upper()}"
        )

    return messages[0]


@router.post("/ingest")
async def ingest_intelligence(
    intelligence_type: IntelligenceType = Body(..., description="Type of intelligence"),
    source: str = Body(..., description="Data source identifier"),
    data: Dict[str, Any] = Body(..., description="Intelligence data payload"),
    symbol: Optional[str] = Body(None, description="Cryptocurrency symbol"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="Additional metadata")
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
            metadata=metadata
        )

        return message

    except Exception as e:
        logger.error(f"Failed to ingest intelligence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process intelligence")


@router.get("/stats")
async def get_intelligence_stats():
    """
    Get intelligence broker statistics.

    Returns:
        dict: Broker statistics including message counts and routing stats
    """
    broker = get_intelligence_broker()
    return broker.get_broker_stats()


@router.get("/connectors")
async def list_connectors(
    intelligence_type: Optional[IntelligenceType] = Query(None, description="Filter by intelligence type"),
    enabled_only: bool = Query(True, description="Only show enabled connectors")
):
    """
    List all registered data connectors.

    Returns:
        dict: List of data connectors with their configurations
    """
    registry = get_service_registry()

    if intelligence_type:
        connectors = registry.get_connectors_by_type(intelligence_type)
    elif enabled_only:
        connectors = registry.get_enabled_connectors()
    else:
        connectors = registry.get_all_connectors()

    return {
        "total": len(connectors),
        "connectors": connectors
    }


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
