"""
CIAL Agents API Router
Endpoints for agent registration and management
"""

from fastapi import APIRouter, Body, HTTPException, Query

from api.models.intelligence import (
    Agent,
    AgentListResponse,
    AgentRegistration,
    AgentRegistrationResponse,
    AgentStatus,
    AgentStatusUpdate,
    AgentType,
)
from core.agent_registry import get_agent_registry
from infrastructure.config import settings
from infrastructure.logging_config import logger

router = APIRouter()


@router.post("/register", response_model=AgentRegistrationResponse)
async def register_agent(agent: AgentRegistration = Body(...)):  # noqa: B008
    """
    Register a new agent with CIAL.

    Agent Types:
    - trading: Trading decision agent
    - risk: Risk management agent
    - sentiment: Sentiment analysis agent
    - portfolio: Portfolio optimization agent
    - market: Market analysis agent
    - content: Content generation agent

    Returns:
        AgentRegistrationResponse: Registration confirmation with connection details
    """
    try:
        registry = get_agent_registry()
        registry.register_agent(agent)

        # Generate WebSocket URL for real-time intelligence
        websocket_url = f"ws://{settings.HOST}:{settings.PORT}/ws/intelligence/{agent.agent_id}"

        # Determine relevant Kafka topics based on agent capabilities
        kafka_topics = []
        for intel_type in agent.capabilities.intelligence_types:
            topic = f"{intel_type.value}.stream"
            kafka_topics.append(topic)

        return AgentRegistrationResponse(
            success=True,
            agent_id=agent.agent_id,
            message=f"Agent {agent.agent_id} registered successfully",
            websocket_url=websocket_url,
            kafka_topics=kafka_topics,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to register agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error during agent registration"
        ) from e


@router.get("/{agent_id}/status", response_model=Agent)
async def get_agent_status(agent_id: str):
    """
    Get agent status and health information.

    Returns:
        Agent: Complete agent information including status and activity
    """
    registry = get_agent_registry()
    agent = registry.get_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return agent


@router.put("/{agent_id}/status")
async def update_agent_status(agent_id: str, status_update: AgentStatusUpdate = Body(...)):  # noqa: B008
    """
    Update agent status.

    Args:
        agent_id: Agent identifier
        status_update: New status and optional metadata

    Returns:
        dict: Update confirmation
    """
    registry = get_agent_registry()

    success = registry.update_agent_status(
        agent_id=agent_id, status=status_update.status, metadata=status_update.metadata
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return {
        "success": True,
        "agent_id": agent_id,
        "status": status_update.status.value,
        "message": "Agent status updated successfully",
    }


@router.delete("/{agent_id}")
async def unregister_agent(agent_id: str):
    """
    Unregister an agent from CIAL.

    Args:
        agent_id: Agent identifier to unregister

    Returns:
        dict: Unregistration confirmation
    """
    registry = get_agent_registry()
    success = registry.unregister_agent(agent_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return {"success": True, "agent_id": agent_id, "message": "Agent unregistered successfully"}


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    agent_type: AgentType = Query(None, description="Filter by agent type"),  # noqa: B008
    status: AgentStatus = Query(None, description="Filter by status"),  # noqa: B008
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of agents to return"),  # noqa: B008
):
    """
    List all registered agents with optional filtering.

    Args:
        agent_type: Optional filter by agent type
        status: Optional filter by status
        limit: Maximum number of agents to return

    Returns:
        AgentListResponse: List of agents matching filters
    """
    registry = get_agent_registry()

    # Get agents based on filters
    if agent_type:
        agents = registry.get_agents_by_type(agent_type)
    else:
        agents = registry.get_all_agents()

    # Apply status filter if provided
    if status:
        agents = [agent for agent in agents if agent.status == status]

    # Apply limit
    agents = agents[:limit]

    return AgentListResponse(total=len(agents), agents=agents)


@router.get("/stats")
async def get_agent_stats():
    """
    Get agent registry statistics.

    Returns:
        dict: Registry statistics including agent counts by type and status
    """
    registry = get_agent_registry()
    return registry.get_registry_stats()
