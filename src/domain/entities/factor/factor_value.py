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
    value: any

    def __post_init__(self):
        """Validate domain constraints."""
        if self.factor_id <= 0:
            raise ValueError("factor_id must be positive")
        if self.entity_id <= 0:
            raise ValueError("entity_id must be positive")
        

    

   

    def __str__(self) -> str:
        return f"FactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})"