"""
Domain entity for FactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict


@dataclass
class FactorRule:
    """
    Domain entity representing a factor rule.
    Pure domain object containing business logic for factor transformations and validations.
    """
    id: Optional[int]
    factor_id: int
    condition: str
    rule_type: str
    method_ref: Optional[str] = None

    def __post_init__(self):
        """Validate domain constraints."""
        if self.factor_id <= 0:
            raise ValueError("factor_id must be positive")
        if not self.condition.strip():
            raise ValueError("condition cannot be empty")
        if not self.rule_type.strip():
            raise ValueError("rule_type cannot be empty")

    def is_validation_rule(self) -> bool:
        """Check if this is a validation rule."""
        return self.rule_type.lower() == 'validation'

    def is_transformation_rule(self) -> bool:
        """Check if this is a transformation rule."""
        return self.rule_type.lower() == 'transformation'

    def evaluate(self, entity: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate the rule condition against an entity.
        This would be implemented based on specific business requirements.
        """
        # This is a placeholder implementation
        # In a real system, you'd parse and evaluate the condition
        # possibly using a rule engine or expression evaluator
        if not context:
            context = {}
        
        # For now, return True as a placeholder
        # Real implementation would parse self.condition and evaluate it
        return True

    def apply_transformation(self, value: Any, context: Optional[Dict] = None) -> Any:
        """
        Apply transformation rule to a value.
        Only applicable if this is a transformation rule.
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not context:
            context = {}
        
        # Placeholder implementation
        # Real implementation would parse method_ref and apply the transformation
        return value

    def __str__(self) -> str:
        return f"FactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type}, condition={self.condition})"