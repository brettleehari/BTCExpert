"""
CIAL Intelligence Validation Service
Cross-source validation and confidence scoring for intelligence messages
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from api.models.intelligence import IntelligenceMessage, IntelligenceType
from infrastructure.logging_config import logger
from memory.long_term_memory import get_long_term_memory
from memory.short_term_memory import get_short_term_memory


class ValidationResult(str, Enum):
    """Validation result status"""

    VALIDATED = "validated"
    SUSPICIOUS = "suspicious"
    REJECTED = "rejected"
    PENDING = "pending"


class ValidationRule:
    """Base class for validation rules"""

    def __init__(self, rule_id: str, description: str, weight: float = 1.0):
        self.rule_id = rule_id
        self.description = description
        self.weight = weight

    def validate(self, message: IntelligenceMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate intelligence message.

        Args:
            message: Intelligence message to validate
            context: Validation context with historical data

        Returns:
            Dict with validation result
        """
        raise NotImplementedError


class PriceDeviationRule(ValidationRule):
    """Validate that price doesn't deviate too much from historical average"""

    def __init__(self, max_deviation_percent: float = 20.0):
        super().__init__(
            rule_id="price_deviation",
            description="Check price deviation from historical average",
            weight=1.0,
        )
        self.max_deviation_percent = max_deviation_percent

    def validate(self, message: IntelligenceMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate price deviation."""
        if message.type != IntelligenceType.PRICE:
            return {"passed": True, "confidence": 1.0, "reason": "Not applicable"}

        current_price = message.data.get("current_price", 0)
        if current_price == 0:
            return {"passed": False, "confidence": 0.0, "reason": "Invalid price"}

        # Get historical average from context
        historical_prices = context.get("historical_prices", [])
        if not historical_prices:
            return {"passed": True, "confidence": 0.7, "reason": "No historical data"}

        avg_price = sum(historical_prices) / len(historical_prices)
        deviation = abs((current_price - avg_price) / avg_price) * 100

        if deviation > self.max_deviation_percent:
            return {
                "passed": False,
                "confidence": 0.3,
                "reason": f"Price deviation {deviation:.2f}% exceeds threshold {self.max_deviation_percent}%",
                "deviation_percent": deviation,
            }

        # Higher confidence for smaller deviations
        confidence = 1.0 - (deviation / self.max_deviation_percent) * 0.3

        return {
            "passed": True,
            "confidence": confidence,
            "reason": f"Price within acceptable range (deviation: {deviation:.2f}%)",
            "deviation_percent": deviation,
        }


class CrossSourceValidationRule(ValidationRule):
    """Validate intelligence against other sources"""

    def __init__(self, min_sources: int = 2, max_variance_percent: float = 5.0):
        super().__init__(
            rule_id="cross_source", description="Validate against multiple sources", weight=1.5
        )
        self.min_sources = min_sources
        self.max_variance_percent = max_variance_percent

    def validate(self, message: IntelligenceMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate across multiple sources."""
        if message.type != IntelligenceType.PRICE:
            return {"passed": True, "confidence": 1.0, "reason": "Not applicable"}

        current_price = message.data.get("current_price", 0)
        other_sources = context.get("other_sources", [])

        if len(other_sources) < self.min_sources - 1:
            return {
                "passed": True,
                "confidence": 0.6,
                "reason": f"Insufficient sources for validation ({len(other_sources) + 1})",
            }

        # Calculate variance with other sources
        all_prices = [current_price] + other_sources
        avg_price = sum(all_prices) / len(all_prices)
        max_variance = max(abs(p - avg_price) / avg_price * 100 for p in all_prices)

        if max_variance > self.max_variance_percent:
            return {
                "passed": False,
                "confidence": 0.5,
                "reason": f"High variance across sources: {max_variance:.2f}%",
                "variance_percent": max_variance,
                "sources_count": len(all_prices),
            }

        confidence = 1.0 - (max_variance / self.max_variance_percent) * 0.2

        return {
            "passed": True,
            "confidence": confidence,
            "reason": f"Validated across {len(all_prices)} sources (variance: {max_variance:.2f}%)",
            "variance_percent": max_variance,
            "sources_count": len(all_prices),
        }


class DataCompletenessRule(ValidationRule):
    """Validate that required data fields are present"""

    def __init__(self):
        super().__init__(
            rule_id="data_completeness", description="Check for required data fields", weight=0.8
        )

        # Required fields by intelligence type
        self.required_fields = {
            IntelligenceType.PRICE: ["current_price"],
            IntelligenceType.SENTIMENT: ["sentiment_score"],
            IntelligenceType.WHALE: ["amount_usd", "from_address", "to_address"],
            IntelligenceType.TECHNICAL: ["indicator", "value"],
        }

    def validate(self, message: IntelligenceMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data completeness."""
        required = self.required_fields.get(message.type, [])

        if not required:
            return {"passed": True, "confidence": 1.0, "reason": "No required fields"}

        missing_fields = [field for field in required if field not in message.data]

        if missing_fields:
            return {
                "passed": False,
                "confidence": 0.3,
                "reason": f"Missing required fields: {', '.join(missing_fields)}",
                "missing_fields": missing_fields,
            }

        # Check for additional valuable fields
        optional_fields = {
            IntelligenceType.PRICE: ["volume_24h", "market_cap", "price_change_percentage_24h"],
            IntelligenceType.SENTIMENT: ["confidence", "source_count"],
        }

        optional = optional_fields.get(message.type, [])
        present_optional = [field for field in optional if field in message.data]

        confidence = 0.8 + (len(present_optional) / len(optional) * 0.2) if optional else 1.0

        return {
            "passed": True,
            "confidence": confidence,
            "reason": f"All required fields present ({len(present_optional)}/{len(optional)} optional fields)",
            "optional_fields_present": len(present_optional),
        }


class SourceReliabilityRule(ValidationRule):
    """Validate based on source reliability score"""

    def __init__(self, min_reliability: float = 0.5):
        super().__init__(
            rule_id="source_reliability", description="Check source reliability", weight=1.2
        )
        self.min_reliability = min_reliability

    def validate(self, message: IntelligenceMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate source reliability."""
        source_reliability = context.get("source_reliability", 0.8)

        if source_reliability < self.min_reliability:
            return {
                "passed": False,
                "confidence": source_reliability,
                "reason": f"Source reliability {source_reliability:.2f} below threshold {self.min_reliability}",
                "source_reliability": source_reliability,
            }

        return {
            "passed": True,
            "confidence": source_reliability,
            "reason": f"Source is reliable ({source_reliability:.2f})",
            "source_reliability": source_reliability,
        }


class TimelinessRule(ValidationRule):
    """Validate that data is recent and timely"""

    def __init__(self, max_age_seconds: int = 300):
        super().__init__(rule_id="timeliness", description="Check data freshness", weight=0.7)
        self.max_age_seconds = max_age_seconds

    def validate(self, message: IntelligenceMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate timeliness."""
        age_seconds = (datetime.utcnow() - message.timestamp).total_seconds()

        if age_seconds > self.max_age_seconds:
            return {
                "passed": False,
                "confidence": 0.5,
                "reason": f"Data is stale ({age_seconds:.0f}s old, max: {self.max_age_seconds}s)",
                "age_seconds": age_seconds,
            }

        # Confidence decreases with age
        confidence = 1.0 - (age_seconds / self.max_age_seconds) * 0.3

        return {
            "passed": True,
            "confidence": confidence,
            "reason": f"Data is fresh ({age_seconds:.0f}s old)",
            "age_seconds": age_seconds,
        }


class IntelligenceValidator:
    """
    Intelligence validation service.

    Validates intelligence messages using multiple rules and provides
    confidence scoring.
    """

    def __init__(self):
        self.stm = get_short_term_memory()
        self.ltm = get_long_term_memory()

        # Initialize validation rules
        self.rules: List[ValidationRule] = [
            PriceDeviationRule(max_deviation_percent=20.0),
            CrossSourceValidationRule(min_sources=2, max_variance_percent=5.0),
            DataCompletenessRule(),
            SourceReliabilityRule(min_reliability=0.5),
            TimelinessRule(max_age_seconds=300),
        ]

        logger.info(f"IntelligenceValidator initialized with {len(self.rules)} rules")

    async def validate(self, message: IntelligenceMessage) -> Dict[str, Any]:
        """
        Validate intelligence message.

        Args:
            message: Intelligence message to validate

        Returns:
            Dict with validation results
        """
        # Build validation context
        context = await self._build_context(message)

        # Run all validation rules
        rule_results = []
        total_weight = 0.0
        weighted_confidence = 0.0
        all_passed = True

        for rule in self.rules:
            try:
                result = rule.validate(message, context)
                result["rule_id"] = rule.rule_id
                result["rule_description"] = rule.description
                result["weight"] = rule.weight

                rule_results.append(result)

                if result["passed"]:
                    weighted_confidence += result["confidence"] * rule.weight
                    total_weight += rule.weight
                else:
                    all_passed = False
                    # Penalize overall confidence
                    weighted_confidence += result.get("confidence", 0.0) * rule.weight * 0.5
                    total_weight += rule.weight

            except Exception as e:
                logger.error(f"Validation rule {rule.rule_id} failed: {e}", exc_info=True)
                rule_results.append(
                    {
                        "rule_id": rule.rule_id,
                        "passed": False,
                        "confidence": 0.5,
                        "reason": f"Rule execution error: {str(e)}",
                    }
                )

        # Calculate overall confidence
        overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5

        # Determine validation status
        if overall_confidence >= 0.8 and all_passed:
            status = ValidationResult.VALIDATED
        elif overall_confidence >= 0.5:
            status = ValidationResult.SUSPICIOUS
        else:
            status = ValidationResult.REJECTED

        validation_result = {
            "status": status.value,
            "confidence": overall_confidence,
            "rules_passed": sum(1 for r in rule_results if r["passed"]),
            "rules_total": len(rule_results),
            "rule_results": rule_results,
            "validated_at": datetime.utcnow().isoformat(),
            "message_id": message.id,
        }

        logger.info(
            f"Validation complete: {status.value}",
            message_id=message.id,
            confidence=overall_confidence,
            rules_passed=f"{validation_result['rules_passed']}/{validation_result['rules_total']}",
        )

        return validation_result

    async def _build_context(self, message: IntelligenceMessage) -> Dict[str, Any]:
        """
        Build validation context with historical and cross-source data.

        Args:
            message: Intelligence message

        Returns:
            Dict with validation context
        """
        context = {}

        try:
            # Get historical prices for price intelligence
            if message.type == IntelligenceType.PRICE and message.symbol:
                # Get recent prices from STM
                recent_intelligence = self.stm.get_recent_intelligence(
                    intelligence_type=message.type, symbol=message.symbol, limit=10
                )

                historical_prices = [
                    intel.get("data", {}).get("current_price", 0)
                    for intel in recent_intelligence
                    if intel.get("data", {}).get("current_price")
                ]

                context["historical_prices"] = historical_prices

                # Get prices from other sources
                other_sources = [
                    intel.get("data", {}).get("current_price")
                    for intel in recent_intelligence
                    if intel.get("source") != message.source
                    and intel.get("data", {}).get("current_price")
                ]

                context["other_sources"] = other_sources[:5]  # Limit to 5 sources

            # Get source reliability from service registry
            from core.service_registry import get_service_registry

            registry = get_service_registry()
            connector = registry.get_connector(message.source)

            if connector:
                context["source_reliability"] = connector.reliability_score
            else:
                context["source_reliability"] = 0.8  # Default

        except Exception as e:
            logger.warning(f"Failed to build validation context: {e}")

        return context

    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule."""
        self.rules.append(rule)
        logger.info(f"Added validation rule: {rule.rule_id}")

    def remove_rule(self, rule_id: str):
        """Remove a validation rule."""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Removed validation rule: {rule_id}")

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get list of validation rules."""
        return [
            {"rule_id": rule.rule_id, "description": rule.description, "weight": rule.weight}
            for rule in self.rules
        ]


# Global validator instance
_validator: Optional[IntelligenceValidator] = None


def get_intelligence_validator() -> IntelligenceValidator:
    """
    Get the global intelligence validator instance.
    Uses singleton pattern.

    Returns:
        IntelligenceValidator: Global validator
    """
    global _validator
    if _validator is None:
        _validator = IntelligenceValidator()
    return _validator
