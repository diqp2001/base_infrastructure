"""
src/domain/entities/factor/factor_dependency.py

Domain entity for factor dependencies - pure domain logic without infrastructure concerns.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FactorDependency:
    """
    Domain entity representing a dependency relationship between two factors.
    
    This entity captures the relationship where one factor (dependent) depends on 
    another factor (independent) for its calculation.
    """
    
    dependent_factor_id: int
    independent_factor_id: int
    id: Optional[int] = None
    
    def __post_init__(self):
        """Validate the factor dependency relationship."""
        if self.dependent_factor_id == self.independent_factor_id:
            raise ValueError("A factor cannot depend on itself")
        
        if self.dependent_factor_id <= 0 or self.independent_factor_id <= 0:
            raise ValueError("Factor IDs must be positive integers")
    
    def __str__(self) -> str:
        return f"FactorDependency(dependent={self.dependent_factor_id}, independent={self.independent_factor_id})"
    
    def __repr__(self) -> str:
        return (f"FactorDependency(id={self.id}, dependent_factor_id={self.dependent_factor_id}, "
                f"independent_factor_id={self.independent_factor_id})")