"""
CIAL Validation API Router
Endpoints for intelligence validation and confidence scoring
"""

from api.models.intelligence import IntelligenceMessage, IntelligenceType
from core.service_registry import get_service_registry
from fastapi import APIRouter, Body, HTTPException
from infrastructure.logging_config import logger
from validation.intelligence_validator import get_intelligence_validator

router = APIRouter()


@router.post("/validate")
async def validate_intelligence(message: IntelligenceMessage = Body(...)):  # noqa: B008
    """
    Validate an intelligence message using all validation rules.

    Args:
        message: Intelligence message to validate

    Returns:
        dict: Validation results with confidence score
    """
    try:
        validator = get_intelligence_validator()
        result = await validator.validate(message)

        return result

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Validation failed") from e


@router.get("/rules")
async def get_validation_rules():
    """
    Get list of active validation rules.

    Returns:
        dict: List of validation rules with descriptions
    """
    validator = get_intelligence_validator()
    rules = validator.get_rules()

    return {"total_rules": len(rules), "rules": rules}


@router.get("/source-reliability")
async def get_source_reliability(source: str | None = None):
    """
    Get reliability scores for data sources.

    Args:
        source: Optional specific source to query

    Returns:
        dict: Source reliability information
    """
    registry = get_service_registry()

    if source:
        connector = registry.get_connector(source)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Source {source} not found")

        health = registry.get_health_status(source)

        return {
            "source": source,
            "reliability_score": connector.reliability_score,
            "enabled": connector.enabled,
            "health": health.model_dump() if health else None,
        }

    # Get all sources
    connectors = registry.get_all_connectors()

    sources_info = []
    for connector in connectors:
        health = registry.get_health_status(connector.connector_id)
        sources_info.append(
            {
                "source": connector.connector_id,
                "name": connector.name,
                "reliability_score": connector.reliability_score,
                "enabled": connector.enabled,
                "intelligence_types": [t.value for t in connector.intelligence_types],
                "healthy": health.healthy if health else False,
            }
        )

    return {"total_sources": len(sources_info), "sources": sources_info}


@router.get("/cross-check/{intelligence_type}/{symbol}")
async def cross_check_intelligence(intelligence_type: str, symbol: str):
    """
    Cross-check intelligence across multiple sources.

    Args:
        intelligence_type: Type of intelligence (price, sentiment, etc.)
        symbol: Cryptocurrency symbol

    Returns:
        dict: Cross-source comparison
    """
    try:
        intel_type = IntelligenceType(intelligence_type)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid intelligence type: {intelligence_type}"
        ) from e

    # Get recent intelligence from multiple sources
    from memory.short_term_memory import get_short_term_memory

    stm = get_short_term_memory()

    recent_intel = stm.get_recent_intelligence(
        intelligence_type=intel_type, symbol=symbol, limit=20
    )

    if not recent_intel:
        raise HTTPException(status_code=404, detail=f"No intelligence found for {symbol}")

    # Group by source
    by_source: dict[str, list[dict]] = {}
    for intel in recent_intel:
        source = intel.get("source", "unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(intel)

    # Calculate statistics for price intelligence
    if intel_type == IntelligenceType.PRICE:
        source_prices = {}
        for source, messages in by_source.items():
            prices = [
                msg.get("data", {}).get("current_price", 0)
                for msg in messages
                if msg.get("data", {}).get("current_price")
            ]
            if prices:
                source_prices[source] = {
                    "latest_price": prices[0],
                    "average_price": sum(prices) / len(prices),
                    "sample_count": len(prices),
                }

        if source_prices:
            all_latest = [data["latest_price"] for data in source_prices.values()]
            avg_latest = sum(all_latest) / len(all_latest)
            max_deviation = max(abs(p - avg_latest) / avg_latest * 100 for p in all_latest)

            return {
                "intelligence_type": intelligence_type,
                "symbol": symbol,
                "sources_count": len(source_prices),
                "average_price": avg_latest,
                "max_deviation_percent": max_deviation,
                "by_source": source_prices,
                "consensus": (
                    "high" if max_deviation < 2 else "medium" if max_deviation < 5 else "low"
                ),
            }

    return {
        "intelligence_type": intelligence_type,
        "symbol": symbol,
        "sources_count": len(by_source),
        "by_source": {source: len(messages) for source, messages in by_source.items()},
    }


@router.get("/consensus/{symbol}")
async def get_consensus(symbol: str, intelligence_type: str | None = "price"):
    """
    Get consensus intelligence for a symbol.

    Aggregates intelligence from multiple sources and provides
    consensus view with confidence scoring.

    Args:
        symbol: Cryptocurrency symbol
        intelligence_type: Type of intelligence (default: price)

    Returns:
        dict: Consensus intelligence
    """
    try:
        intel_type = IntelligenceType(intelligence_type)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid intelligence type: {intelligence_type}"
        ) from e

    from memory.short_term_memory import get_short_term_memory

    stm = get_short_term_memory()

    recent_intel = stm.get_recent_intelligence(
        intelligence_type=intel_type, symbol=symbol, limit=10
    )

    if not recent_intel:
        raise HTTPException(status_code=404, detail=f"No intelligence found for {symbol}")

    # Calculate consensus for price
    if intel_type == IntelligenceType.PRICE:
        prices = [
            msg.get("data", {}).get("current_price", 0)
            for msg in recent_intel
            if msg.get("data", {}).get("current_price")
        ]

        if not prices:
            raise HTTPException(status_code=404, detail="No valid price data found")

        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        variance = max_price - min_price
        variance_percent = (variance / avg_price) * 100

        # Determine confidence based on variance
        if variance_percent < 1:
            confidence = "high"
        elif variance_percent < 3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "symbol": symbol,
            "intelligence_type": intelligence_type,
            "consensus_price": avg_price,
            "price_range": {
                "min": min_price,
                "max": max_price,
                "variance_percent": variance_percent,
            },
            "confidence": confidence,
            "sample_size": len(prices),
            "sources": len({msg.get("source") for msg in recent_intel}),
        }

    # Generic response for other types
    return {
        "symbol": symbol,
        "intelligence_type": intelligence_type,
        "sample_size": len(recent_intel),
        "sources": len({msg.get("source") for msg in recent_intel}),
    }


@router.get("/stats")
async def get_validation_stats():
    """
    Get validation statistics.

    Returns:
        dict: Validation system statistics
    """
    validator = get_intelligence_validator()
    registry = get_service_registry()

    rules = validator.get_rules()
    registry_stats = registry.get_registry_stats()

    return {
        "validation_rules": len(rules),
        "registered_sources": registry_stats.get("total_connectors", 0),
        "healthy_sources": registry_stats.get("healthy_connectors", 0),
        "overall_reliability": registry_stats.get("overall_success_rate", 0.0),
    }
