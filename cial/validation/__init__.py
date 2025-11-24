"""
CIAL Intelligence Validation

Cross-source validation and confidence scoring for intelligence messages.

Components:
- IntelligenceValidator: Main validation service
- ValidationRule: Base class for validation rules
- Built-in rules: Price deviation, cross-source, completeness, reliability, timeliness
"""

from .intelligence_validator import (
    IntelligenceValidator,
    ValidationRule,
    ValidationResult,
    PriceDeviationRule,
    CrossSourceValidationRule,
    DataCompletenessRule,
    SourceReliabilityRule,
    TimelinessRule,
    get_intelligence_validator
)

__all__ = [
    'IntelligenceValidator',
    'ValidationRule',
    'ValidationResult',
    'PriceDeviationRule',
    'CrossSourceValidationRule',
    'DataCompletenessRule',
    'SourceReliabilityRule',
    'TimelinessRule',
    'get_intelligence_validator'
]
