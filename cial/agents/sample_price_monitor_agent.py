"""
Sample Price Monitor Agent
Demonstrates BaseAgent implementation for price monitoring and alerting
"""

from agents.base_agent import AgentDecision, AgentDecisionType, BaseAgent
from api.models.intelligence import (
    AgentCapabilities,
    AgentType,
    IntelligenceImportance,
    IntelligenceMessage,
    IntelligenceType,
)
from infrastructure.logging_config import logger


class PriceMonitorAgent(BaseAgent):
    """
    Sample agent that monitors cryptocurrency prices and generates alerts.

    Features:
    - Monitors price changes
    - Generates alerts on significant moves
    - Tracks price trends
    - Makes simple buy/sell recommendations
    """

    def __init__(
        self,
        agent_id: str,
        symbols: list[str],
        alert_threshold: float = 5.0,  # Alert on 5% change
        recommendation_threshold: float = 10.0,  # Recommend on 10% change
    ):
        # Define agent capabilities
        capabilities = AgentCapabilities(
            intelligence_types=[IntelligenceType.PRICE],
            symbols=symbols,
            min_importance=IntelligenceImportance.NORMAL,
            real_time=True,
        )

        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.MARKET,
            capabilities=capabilities,
            metadata={
                "alert_threshold": alert_threshold,
                "recommendation_threshold": recommendation_threshold,
            },
        )

        self.alert_threshold = alert_threshold
        self.recommendation_threshold = recommendation_threshold
        self.baseline_prices = {}  # Track baseline for comparisons

    async def on_start(self):
        """Initialize baseline prices when agent starts."""
        logger.info(f"PriceMonitorAgent {self.agent_id} initializing baselines")

        # Load current prices for all symbols
        for symbol in self.capabilities.symbols:
            current_price = await self.get_current_price(symbol)
            if current_price:
                self.baseline_prices[symbol] = current_price.get("current_price", 0)
                logger.info(f"Baseline set for {symbol}", price=self.baseline_prices[symbol])

    async def process_intelligence(self, message: IntelligenceMessage) -> AgentDecision | None:
        """
        Process price intelligence and make decisions.

        Args:
            message: Price intelligence message

        Returns:
            Optional[AgentDecision]: Decision made
        """
        # Extract price data
        current_price = message.data.get("current_price", 0)
        price_change_24h = message.data.get("price_change_percentage_24h", 0)
        symbol = message.symbol

        if not symbol or current_price == 0:
            return None

        logger.debug(
            "Processing price update",
            symbol=symbol,
            price=current_price,
            change_24h=price_change_24h,
        )

        # Update baseline if not set
        if symbol not in self.baseline_prices:
            self.baseline_prices[symbol] = current_price

        # Calculate change from baseline
        baseline = self.baseline_prices[symbol]
        baseline_change = ((current_price - baseline) / baseline) * 100

        # Decision logic
        decision_type = AgentDecisionType.HOLD
        confidence = 0.5
        reasoning = f"{symbol} price stable at ${current_price:.2f}"

        # Check for significant moves
        if abs(baseline_change) >= self.recommendation_threshold:
            # Strong recommendation
            if baseline_change > 0:
                decision_type = AgentDecisionType.SELL
                reasoning = f"{symbol} up {baseline_change:.2f}% from baseline - take profits"
                confidence = min(0.9, 0.6 + (abs(baseline_change) / 100))
            else:
                decision_type = AgentDecisionType.BUY
                reasoning = (
                    f"{symbol} down {abs(baseline_change):.2f}% from baseline - buying opportunity"
                )
                confidence = min(0.9, 0.6 + (abs(baseline_change) / 100))

        elif abs(baseline_change) >= self.alert_threshold:
            # Alert on moderate moves
            decision_type = AgentDecisionType.ALERT
            direction = "up" if baseline_change > 0 else "down"
            reasoning = f"{symbol} {direction} {abs(baseline_change):.2f}% from baseline"
            confidence = 0.7

        elif abs(price_change_24h) >= self.alert_threshold:
            # Alert on 24h volatility
            decision_type = AgentDecisionType.ALERT
            direction = "up" if price_change_24h > 0 else "down"
            reasoning = f"{symbol} volatile: {direction} {abs(price_change_24h):.2f}% in 24h"
            confidence = 0.6

        # Create decision
        decision = AgentDecision(
            decision_type=decision_type,
            confidence=confidence,
            reasoning=reasoning,
            data={
                "symbol": symbol,
                "current_price": current_price,
                "baseline_price": baseline,
                "baseline_change_pct": baseline_change,
                "price_change_24h_pct": price_change_24h,
                "volume_24h": message.data.get("volume_24h", 0),
                "market_cap": message.data.get("market_cap", 0),
            },
            metadata={
                "intelligence_id": message.id,
                "intelligence_source": message.source,
                "alert_threshold": self.alert_threshold,
                "recommendation_threshold": self.recommendation_threshold,
            },
        )

        return decision

    async def execute_decision(self, decision: AgentDecision):
        """
        Execute decision by logging and potentially triggering actions.

        In a real implementation, this could:
        - Send notifications
        - Execute trades
        - Update dashboards
        - Trigger other agents

        Args:
            decision: Decision to execute
        """
        symbol = decision.data.get("symbol", "UNKNOWN")
        current_price = decision.data.get("current_price", 0)

        if decision.decision_type == AgentDecisionType.BUY:
            logger.info(
                f"🟢 BUY RECOMMENDATION: {symbol}",
                price=current_price,
                confidence=decision.confidence,
                reasoning=decision.reasoning,
            )
            # In production: Execute buy order or send alert

        elif decision.decision_type == AgentDecisionType.SELL:
            logger.info(
                f"🔴 SELL RECOMMENDATION: {symbol}",
                price=current_price,
                confidence=decision.confidence,
                reasoning=decision.reasoning,
            )
            # In production: Execute sell order or send alert

        elif decision.decision_type == AgentDecisionType.ALERT:
            logger.info(
                f"⚠️  PRICE ALERT: {symbol}", price=current_price, reasoning=decision.reasoning
            )
            # In production: Send push notification

        else:
            logger.debug(f"HOLD: {symbol}", price=current_price)

    async def reset_baseline(self, symbol: str | None = None):
        """
        Reset baseline price(s).

        Args:
            symbol: Specific symbol to reset (None = reset all)
        """
        if symbol:
            current_price = await self.get_current_price(symbol)
            if current_price:
                self.baseline_prices[symbol] = current_price.get("current_price", 0)
                logger.info(f"Baseline reset for {symbol}: ${self.baseline_prices[symbol]:.2f}")
        else:
            for sym in self.capabilities.symbols:
                current_price = await self.get_current_price(sym)
                if current_price:
                    self.baseline_prices[sym] = current_price.get("current_price", 0)
            logger.info("All baselines reset")

    def get_baselines(self) -> dict:
        """Get current baseline prices."""
        return self.baseline_prices.copy()
