"""
CIAL Memory API Router
Endpoints for agent memory management (STM & LTM)
"""

from fastapi import APIRouter, HTTPException, Path, Body
from typing import Optional, Dict, Any

from memory.short_term_memory import get_short_term_memory
from api.models.intelligence import IntelligenceType
from infrastructure.logging_config import logger

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


@router.post("/ltm/{agent_id}/learn")
async def store_learning(agent_id: str):
    """
    Store agent learning outcome in long-term memory.
    """
    # TODO: Implement learning storage
    return {
        "agent_id": agent_id,
        "status": "pending_implementation",
        "message": "Learning storage endpoint will be implemented in Session 6"
    }
