"""
CIAL Base Agent Interface
Standardized framework for building intelligent crypto agents
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from api.models.intelligence import (
    AgentCapabilities,
    AgentStatus,
    AgentType,
    IntelligenceImportance,
    IntelligenceMessage,
    IntelligenceType,
)
from infrastructure.logging_config import logger
from memory.long_term_memory import get_long_term_memory
from memory.short_term_memory import get_short_term_memory


class AgentDecisionType(str, Enum):
    """Types of agent decisions"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    ALERT = "alert"
    ANALYZE = "analyze"
    LEARN = "learn"


class AgentDecision:
    """
    Represents an agent decision with metadata.
    """

    def __init__(
        self,
        decision_type: AgentDecisionType,
        confidence: float,
        reasoning: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = f"decision_{uuid.uuid4().hex[:12]}"
        self.decision_type = decision_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.data = data or {}
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            "id": self.id,
            "decision_type": self.decision_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """
    Base class for all CIAL agents.

    Provides:
    - Standardized lifecycle management
    - Intelligence consumption
    - Memory access (STM/LTM)
    - Decision tracking
    - Context management
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        capabilities: AgentCapabilities,
        metadata: dict[str, Any] | None = None,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.metadata = metadata or {}
        self.status = AgentStatus.INITIALIZING

        # Memory access
        self.stm = get_short_term_memory()
        self.ltm = get_long_term_memory()

        # Agent state
        self._context: dict[str, Any] = {}
        self._decisions: list[AgentDecision] = []
        self._intelligence_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

        logger.info(
            f"Agent initialized: {self.agent_id}",
            type=self.agent_type.value,
            capabilities=self.capabilities.model_dump(),
        )

    # Lifecycle Management

    async def start(self):
        """
        Start the agent.
        Begins processing intelligence and making decisions.
        """
        if self._running:
            logger.warning(f"Agent {self.agent_id} already running")
            return

        self._running = True
        self.status = AgentStatus.ACTIVE

        # Call custom initialization
        await self.on_start()

        # Start processing loop
        self._task = asyncio.create_task(self._processing_loop())

        logger.info(f"Agent started: {self.agent_id}")

    async def stop(self):
        """
        Stop the agent gracefully.
        """
        if not self._running:
            return

        self._running = False
        self.status = AgentStatus.STOPPED

        # Call custom cleanup
        await self.on_stop()

        # Cancel processing task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info(f"Agent stopped: {self.agent_id}")

    async def pause(self):
        """Pause agent processing."""
        if self.status == AgentStatus.ACTIVE:
            self.status = AgentStatus.PAUSED
            await self.on_pause()
            logger.info(f"Agent paused: {self.agent_id}")

    async def resume(self):
        """Resume agent processing."""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.ACTIVE
            await self.on_resume()
            logger.info(f"Agent resumed: {self.agent_id}")

    # Intelligence Processing

    async def receive_intelligence(self, message: IntelligenceMessage):
        """
        Receive intelligence message from CIAL broker.

        Args:
            message: Intelligence message to process
        """
        if self.status != AgentStatus.ACTIVE:
            logger.debug(f"Agent {self.agent_id} not active, ignoring intelligence")
            return

        # Filter by capabilities
        if not self._should_process(message):
            return

        # Add to queue for processing
        await self._intelligence_queue.put(message)

        logger.debug(
            f"Intelligence queued: {message.id}", agent=self.agent_id, type=message.type.value
        )

    def _should_process(self, message: IntelligenceMessage) -> bool:
        """
        Check if agent should process this intelligence.

        Args:
            message: Intelligence message

        Returns:
            bool: True if agent should process
        """
        # Check intelligence type
        if message.type not in self.capabilities.intelligence_types:
            return False

        # Check symbol filter
        if self.capabilities.symbols and message.symbol:
            if message.symbol not in self.capabilities.symbols:
                return False

        # Check importance threshold
        importance_order = {
            IntelligenceImportance.LOW: 0,
            IntelligenceImportance.NORMAL: 1,
            IntelligenceImportance.CRITICAL: 2,
        }

        min_importance = importance_order.get(self.capabilities.min_importance, 0)
        message_importance = importance_order.get(message.importance, 0)

        if message_importance < min_importance:
            return False

        return True

    async def _processing_loop(self):
        """
        Main processing loop for the agent.
        Continuously processes intelligence from queue.
        """
        logger.info(f"Agent processing loop started: {self.agent_id}")

        try:
            while self._running:
                try:
                    # Get intelligence from queue (with timeout)
                    message = await asyncio.wait_for(self._intelligence_queue.get(), timeout=1.0)

                    # Process the intelligence
                    await self._process_intelligence(message)

                except asyncio.TimeoutError:
                    # No intelligence in queue, continue
                    continue
                except Exception as e:
                    logger.error(
                        f"Error in processing loop: {e}", agent=self.agent_id, exc_info=True
                    )

        except asyncio.CancelledError:
            logger.info(f"Agent processing loop cancelled: {self.agent_id}")
        finally:
            logger.info(f"Agent processing loop stopped: {self.agent_id}")

    async def _process_intelligence(self, message: IntelligenceMessage):
        """
        Process intelligence message and make decisions.

        Args:
            message: Intelligence message to process
        """
        try:
            # Update context
            await self._update_context(message)

            # Call custom processing
            decision = await self.process_intelligence(message)

            if decision:
                # Store decision
                self._decisions.append(decision)

                # Save to STM
                self.stm.store_agent_decision(agent_id=self.agent_id, decision=decision.to_dict())

                # Execute decision
                await self.execute_decision(decision)

                logger.info(
                    f"Decision made: {decision.decision_type.value}",
                    agent=self.agent_id,
                    confidence=decision.confidence,
                    intelligence_id=message.id,
                )

        except Exception as e:
            logger.error(
                f"Failed to process intelligence: {e}",
                agent=self.agent_id,
                message_id=message.id,
                exc_info=True,
            )

    async def _update_context(self, message: IntelligenceMessage):
        """
        Update agent's context with new intelligence.

        Args:
            message: Intelligence message
        """
        # Update last seen intelligence
        self._context[f"last_{message.type.value}"] = {
            "id": message.id,
            "data": message.data,
            "timestamp": message.timestamp.isoformat(),
        }

        # Update symbol-specific context
        if message.symbol:
            symbol_key = f"symbol_{message.symbol}"
            if symbol_key not in self._context:
                self._context[symbol_key] = {}

            self._context[symbol_key][message.type.value] = message.data

        # Save context to STM
        self.stm.store_agent_context(agent_id=self.agent_id, context=self._context)

    # Memory Access Helpers

    async def get_current_price(self, symbol: str) -> dict[str, Any] | None:
        """Get current price for a symbol from STM."""
        return self.stm.get_current_price(symbol)

    async def get_price_history(self, symbol: str, days: int = 7) -> list[dict[str, Any]]:
        """Get historical prices from LTM."""
        from datetime import timedelta

        start_time = datetime.utcnow() - timedelta(days=days)
        return await self.ltm.get_historical_prices(symbol, start_time)

    async def get_recent_decisions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent decisions from STM."""
        return self.stm.get_agent_decisions(self.agent_id, limit)

    def get_context(self) -> dict[str, Any]:
        """Get current agent context."""
        return self._context.copy()

    # Abstract Methods (must be implemented by subclasses)

    @abstractmethod
    async def process_intelligence(self, message: IntelligenceMessage) -> AgentDecision | None:
        """
        Process intelligence and make a decision.

        Args:
            message: Intelligence message to process

        Returns:
            Optional[AgentDecision]: Decision made (or None)
        """
        pass

    @abstractmethod
    async def execute_decision(self, decision: AgentDecision):
        """
        Execute a decision made by the agent.

        Args:
            decision: Decision to execute
        """
        pass

    # Lifecycle Hooks (optional overrides)

    async def on_start(self):
        """Called when agent starts. Override for custom initialization."""
        pass

    async def on_stop(self):
        """Called when agent stops. Override for custom cleanup."""
        pass

    async def on_pause(self):
        """Called when agent pauses. Override for custom pause logic."""
        pass

    async def on_resume(self):
        """Called when agent resumes. Override for custom resume logic."""
        pass

    # Utility Methods

    def get_stats(self) -> dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dict: Agent stats including decision counts
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "total_decisions": len(self._decisions),
            "decisions_by_type": self._count_decisions_by_type(),
            "average_confidence": self._average_confidence(),
            "queue_size": self._intelligence_queue.qsize(),
        }

    def _count_decisions_by_type(self) -> dict[str, int]:
        """Count decisions by type."""
        counts = {}
        for decision in self._decisions:
            decision_type = decision.decision_type.value
            counts[decision_type] = counts.get(decision_type, 0) + 1
        return counts

    def _average_confidence(self) -> float:
        """Calculate average decision confidence."""
        if not self._decisions:
            return 0.0
        total = sum(d.confidence for d in self._decisions)
        return total / len(self._decisions)
