"""
CIAL Agent Registry
Service for agent registration, discovery, and lifecycle management
"""

from datetime import datetime

from api.models.intelligence import (
    Agent,
    AgentRegistration,
    AgentStatus,
    AgentType,
    IntelligenceType,
)
from infrastructure.logging_config import log_agent_activity, logger


class AgentRegistry:
    """
    Central registry for managing agent lifecycle.

    Responsibilities:
    - Agent registration and unregistration
    - Agent discovery and lookup
    - Status tracking and health monitoring
    - Capability-based routing
    """

    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._type_index: dict[AgentType, list[str]] = {}
        self._intelligence_index: dict[IntelligenceType, list[str]] = {}

        logger.info("AgentRegistry initialized")

    def register_agent(self, registration: AgentRegistration) -> Agent:
        """
        Register a new agent with CIAL.

        Args:
            registration: Agent registration information

        Returns:
            Agent: Registered agent object

        Raises:
            ValueError: If agent_id already exists
        """
        if registration.agent_id in self._agents:
            raise ValueError(f"Agent {registration.agent_id} is already registered")

        # Create agent object
        agent = Agent(
            agent_id=registration.agent_id,
            agent_type=registration.agent_type,
            capabilities=registration.capabilities,
            status=AgentStatus.ACTIVE,
            metadata=registration.metadata,
        )

        # Store agent
        self._agents[agent.agent_id] = agent

        # Update indexes
        self._update_type_index(agent)
        self._update_intelligence_index(agent)

        log_agent_activity(
            agent_id=agent.agent_id,
            action="registered",
            agent_type=agent.agent_type.value,
            capabilities=len(agent.capabilities.intelligence_types),
        )

        logger.info(
            f"Agent registered: {agent.agent_id}",
            agent_type=agent.agent_type.value,
            intelligence_types=agent.capabilities.intelligence_types,
        )

        return agent

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from CIAL.

        Args:
            agent_id: Agent identifier

        Returns:
            bool: True if unregistered, False if not found
        """
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]

        # Remove from indexes
        self._remove_from_type_index(agent)
        self._remove_from_intelligence_index(agent)

        # Remove agent
        del self._agents[agent_id]

        log_agent_activity(agent_id=agent_id, action="unregistered")

        logger.info(f"Agent unregistered: {agent_id}")

        return True

    def get_agent(self, agent_id: str) -> Agent | None:
        """
        Get agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Optional[Agent]: Agent if found, None otherwise
        """
        return self._agents.get(agent_id)

    def update_agent_status(
        self, agent_id: str, status: AgentStatus, metadata: dict | None = None
    ) -> bool:
        """
        Update agent status.

        Args:
            agent_id: Agent identifier
            status: New status
            metadata: Optional metadata updates

        Returns:
            bool: True if updated, False if agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        old_status = agent.status
        agent.status = status
        agent.last_active = datetime.utcnow()

        if metadata:
            agent.metadata.update(metadata)

        log_agent_activity(
            agent_id=agent_id,
            action="status_updated",
            old_status=old_status.value,
            new_status=status.value,
        )

        logger.info(
            f"Agent status updated: {agent_id}",
            old_status=old_status.value,
            new_status=status.value,
        )

        return True

    def update_agent_activity(self, agent_id: str) -> bool:
        """
        Update agent's last activity timestamp.

        Args:
            agent_id: Agent identifier

        Returns:
            bool: True if updated, False if agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.last_active = datetime.utcnow()
        agent.message_count += 1

        return True

    def get_all_agents(self) -> list[Agent]:
        """
        Get all registered agents.

        Returns:
            List[Agent]: List of all agents
        """
        return list(self._agents.values())

    def get_agents_by_type(self, agent_type: AgentType) -> list[Agent]:
        """
        Get all agents of a specific type.

        Args:
            agent_type: Type of agents to retrieve

        Returns:
            List[Agent]: List of agents matching the type
        """
        agent_ids = self._type_index.get(agent_type, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agents_for_intelligence(
        self, intelligence_type: IntelligenceType, symbol: str | None = None
    ) -> list[Agent]:
        """
        Find agents that should receive specific intelligence.

        Args:
            intelligence_type: Type of intelligence
            symbol: Optional cryptocurrency symbol

        Returns:
            List[Agent]: List of agents interested in this intelligence
        """
        candidate_ids = self._intelligence_index.get(intelligence_type, [])

        matching_agents = []
        for agent_id in candidate_ids:
            agent = self._agents.get(agent_id)
            if not agent or agent.status != AgentStatus.ACTIVE:
                continue

            # Check if agent is interested in this symbol (empty list = all symbols)
            if symbol and agent.capabilities.symbols and symbol not in agent.capabilities.symbols:
                continue

            matching_agents.append(agent)

        return matching_agents

    def get_active_agent_count(self) -> int:
        """
        Get count of active agents.

        Returns:
            int: Number of active agents
        """
        return sum(1 for agent in self._agents.values() if agent.status == AgentStatus.ACTIVE)

    def get_registry_stats(self) -> dict:
        """
        Get registry statistics.

        Returns:
            Dict: Registry statistics
        """
        status_counts = {}
        type_counts = {}

        for agent in self._agents.values():
            # Count by status
            status_counts[agent.status.value] = status_counts.get(agent.status.value, 0) + 1
            # Count by type
            type_counts[agent.agent_type.value] = type_counts.get(agent.agent_type.value, 0) + 1

        return {
            "total_agents": len(self._agents),
            "active_agents": self.get_active_agent_count(),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "total_messages_delivered": sum(agent.message_count for agent in self._agents.values()),
        }

    # Internal index management methods

    def _update_type_index(self, agent: Agent):
        """Update type index when agent is registered."""
        if agent.agent_type not in self._type_index:
            self._type_index[agent.agent_type] = []
        self._type_index[agent.agent_type].append(agent.agent_id)

    def _remove_from_type_index(self, agent: Agent):
        """Remove agent from type index."""
        if agent.agent_type in self._type_index:
            try:
                self._type_index[agent.agent_type].remove(agent.agent_id)
            except ValueError:
                pass

    def _update_intelligence_index(self, agent: Agent):
        """Update intelligence type index when agent is registered."""
        for intel_type in agent.capabilities.intelligence_types:
            if intel_type not in self._intelligence_index:
                self._intelligence_index[intel_type] = []
            self._intelligence_index[intel_type].append(agent.agent_id)

    def _remove_from_intelligence_index(self, agent: Agent):
        """Remove agent from intelligence type indexes."""
        for intel_type in agent.capabilities.intelligence_types:
            if intel_type in self._intelligence_index:
                try:
                    self._intelligence_index[intel_type].remove(agent.agent_id)
                except ValueError:
                    pass


# Global agent registry instance
_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry instance.
    Uses singleton pattern.

    Returns:
        AgentRegistry: Global registry instance
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
