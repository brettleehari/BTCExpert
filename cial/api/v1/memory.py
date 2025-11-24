"""
CIAL Memory API Router
Endpoints for agent memory management (STM & LTM)
"""

from fastapi import APIRouter, HTTPException, Path, Body
from typing import Optional, Dict, Any

from memory.short_term_memory import get_short_term_memory
from memory.long_term_memory import get_long_term_memory
from api.models.intelligence import IntelligenceType
from infrastructure.logging_config import logger
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/stm/{agent_id}/context")
async def get_agent_context(
    agent_id: str = Path(..., description="Agent identifier")
):
    """
    Get agent's short-term memory context.

    Returns:
        dict: Agent's working context from STM
    """
    stm = get_short_term_memory()
    context = stm.get_agent_context(agent_id)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"No context found for agent {agent_id}"
        )

    return {
        "agent_id": agent_id,
        "context": context
    }


@router.post("/stm/{agent_id}/context")
async def store_agent_context(
    agent_id: str = Path(..., description="Agent identifier"),
    context: Dict[str, Any] = Body(..., description="Context data to store"),
    ttl: Optional[int] = Body(86400, description="Time-to-live in seconds")
):
    """
    Store agent's working context in short-term memory.

    Args:
        agent_id: Agent identifier
        context: Context data
        ttl: Time-to-live in seconds (default: 24 hours)

    Returns:
        dict: Storage confirmation
    """
    stm = get_short_term_memory()
    success = stm.store_agent_context(agent_id, context, ttl)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to store agent context")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent context stored successfully",
        "ttl": ttl
    }


@router.post("/stm/{agent_id}/decision")
async def store_agent_decision(
    agent_id: str = Path(..., description="Agent identifier"),
    decision: Dict[str, Any] = Body(..., description="Decision data"),
    ttl: Optional[int] = Body(86400, description="Time-to-live in seconds")
):
    """
    Store agent decision in short-term memory.

    Args:
        agent_id: Agent identifier
        decision: Decision data including action, reasoning, etc.
        ttl: Time-to-live in seconds (default: 24 hours)

    Returns:
        dict: Storage confirmation
    """
    stm = get_short_term_memory()
    success = stm.store_agent_decision(agent_id, decision, ttl)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to store decision")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Decision stored successfully",
        "ttl": ttl
    }


@router.get("/stm/{agent_id}/decisions")
async def get_agent_decisions(
    agent_id: str = Path(..., description="Agent identifier"),
    limit: int = 10
):
    """
    Get agent's recent decisions from short-term memory.

    Args:
        agent_id: Agent identifier
        limit: Maximum number of decisions to return

    Returns:
        dict: Recent decisions (newest first)
    """
    stm = get_short_term_memory()
    decisions = stm.get_agent_decisions(agent_id, limit)

    return {
        "agent_id": agent_id,
        "decisions": decisions,
        "count": len(decisions)
    }


@router.get("/stm/{agent_id}/market-state")
async def get_market_state(agent_id: str = Path(..., description="Agent identifier")):
    """
    Get current market state for decision making.

    Returns:
        dict: Current market state from STM
    """
    stm = get_short_term_memory()
    market_state = stm.get_market_state()

    if market_state is None:
        raise HTTPException(status_code=404, detail="No market state available")

    return {
        "agent_id": agent_id,
        "market_state": market_state
    }


@router.delete("/stm/{agent_id}")
async def clear_agent_memory(agent_id: str = Path(..., description="Agent identifier")):
    """
    Clear all short-term memory data for an agent.

    Args:
        agent_id: Agent identifier

    Returns:
        dict: Clearance confirmation
    """
    stm = get_short_term_memory()
    success = stm.clear_agent_data(agent_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear agent memory")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent memory cleared successfully"
    }


@router.get("/stm/price/{symbol}")
async def get_cached_price(symbol: str = Path(..., description="Cryptocurrency symbol")):
    """
    Get current cached price for a symbol from STM.

    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH)

    Returns:
        dict: Current price data
    """
    stm = get_short_term_memory()
    price_data = stm.get_current_price(symbol.upper())

    if price_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cached price data for {symbol.upper()}"
        )

    return {
        "symbol": symbol.upper(),
        "price_data": price_data
    }


@router.get("/stm/stats")
async def get_stm_stats():
    """
    Get Short-Term Memory statistics.

    Returns:
        dict: STM cache statistics
    """
    stm = get_short_term_memory()
    return stm.get_cache_stats()


@router.get("/ltm/{agent_id}/patterns")
async def get_agent_patterns(agent_id: str):
    """
    Get agent's learned patterns from long-term memory.
    """
    # TODO: Implement LTM pattern retrieval
    return {
        "agent_id": agent_id,
        "status": "pending_implementation",
        "message": "LTM patterns endpoint will be implemented in Session 6"
    }


@router.get("/ltm/intelligence/{intelligence_id}")
async def get_ltm_intelligence(intelligence_id: str):
    """
    Retrieve intelligence from Long-Term Memory by ID.

    Returns:
        dict: Intelligence record from PostgreSQL
    """
    ltm = get_long_term_memory()
    intelligence = await ltm.get_intelligence(intelligence_id)

    if not intelligence:
        raise HTTPException(
            status_code=404,
            detail=f"Intelligence {intelligence_id} not found in LTM"
        )

    return intelligence


@router.get("/ltm/prices/{symbol}/history")
async def get_price_history(
    symbol: str,
    days: int = 7
):
    """
    Get historical price data for a symbol.

    Args:
        symbol: Cryptocurrency symbol
        days: Number of days of history

    Returns:
        list: Historical price records
    """
    ltm = get_long_term_memory()
    start_time = datetime.utcnow() - timedelta(days=days)

    prices = await ltm.get_historical_prices(
        symbol=symbol,
        start_time=start_time,
        limit=1000
    )

    return {
        "symbol": symbol,
        "days": days,
        "total_records": len(prices),
        "prices": prices
    }


@router.get("/ltm/prices/{symbol}/trends")
async def get_price_trends(
    symbol: str,
    days: int = 7
):
    """
    Get price trend analysis for a symbol.

    Args:
        symbol: Cryptocurrency symbol
        days: Number of days to analyze

    Returns:
        dict: Trend analysis including avg, min, max, volatility
    """
    ltm = get_long_term_memory()
    trends = await ltm.get_price_trends(symbol, days)

    if not trends:
        raise HTTPException(
            status_code=404,
            detail=f"No price data found for {symbol}"
        )

    return trends


@router.get("/ltm/sentiment/history")
async def get_sentiment_history(
    symbol: Optional[str] = None,
    days: int = 7
):
    """
    Get historical sentiment data.

    Args:
        symbol: Optional symbol filter
        days: Number of days of history

    Returns:
        list: Historical sentiment records
    """
    ltm = get_long_term_memory()
    sentiment = await ltm.get_sentiment_history(symbol, days)

    return {
        "symbol": symbol or "all",
        "days": days,
        "total_records": len(sentiment),
        "sentiment": sentiment
    }


@router.get("/ltm/whale/movements")
async def get_whale_movements(
    symbol: Optional[str] = None,
    min_amount_usd: float = 1000000,
    days: int = 30
):
    """
    Get whale movement history.

    Args:
        symbol: Optional symbol filter
        min_amount_usd: Minimum transaction amount
        days: Number of days of history

    Returns:
        list: Whale movement records
    """
    ltm = get_long_term_memory()
    movements = await ltm.get_whale_movements(symbol, min_amount_usd, days)

    return {
        "symbol": symbol or "all",
        "min_amount_usd": min_amount_usd,
        "days": days,
        "total_movements": len(movements),
        "movements": movements
    }


@router.get("/ltm/events/critical")
async def get_critical_events(days: int = 7):
    """
    Get recent critical intelligence events.

    Args:
        days: Number of days of history

    Returns:
        list: Critical intelligence records
    """
    ltm = get_long_term_memory()
    events = await ltm.get_critical_events(days)

    return {
        "days": days,
        "total_events": len(events),
        "events": events
    }


@router.get("/ltm/search")
async def search_ltm(
    query: str,
    intelligence_type: Optional[str] = None,
    limit: int = 50
):
    """
    Search intelligence in Long-Term Memory.

    Args:
        query: Search query
        intelligence_type: Optional type filter
        limit: Maximum results

    Returns:
        list: Matching intelligence records
    """
    ltm = get_long_term_memory()
    results = await ltm.search_intelligence(query, intelligence_type, limit)

    return {
        "query": query,
        "intelligence_type": intelligence_type,
        "total_results": len(results),
        "results": results
    }


@router.get("/ltm/stats")
async def get_ltm_stats():
    """
    Get Long-Term Memory statistics.

    Returns:
        dict: LTM statistics including record counts and analytics
    """
    ltm = get_long_term_memory()
    stats = await ltm.get_ltm_stats()

    return stats
