"""
Domain entity for FactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class FactorValue:
    """
    Domain entity representing a factor value.
    Pure domain object without infrastructure concerns.
    """
    id: Optional[int]
    factor_id: int
    entity_id: int
    date: date
    value: Decimal

    def __post_init__(self):
        """Validate domain constraints."""
        if self.factor_id <= 0:
            raise ValueError("factor_id must be positive")
        if self.entity_id <= 0:
            raise ValueError("entity_id must be positive")
        if not isinstance(self.value, Decimal):
            self.value = Decimal(str(self.value))

    def is_valid_for_date_range(self, start_date: date, end_date: date) -> bool:
        """Check if this factor value falls within the specified date range."""
        return start_date <= self.date <= end_date

    def adjust_value(self, multiplier: Decimal) -> 'FactorValue':
        """Create a new FactorValue with adjusted value."""
        return FactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=self.value * multiplier
        )

    def __str__(self) -> str:
        return f"FactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})"