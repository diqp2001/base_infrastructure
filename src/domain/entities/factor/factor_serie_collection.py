"""
Factor Serie Collection domain entity for optimization.

This entity contains a list of factor entities and is used to optimize
factor value creation/population in the database. This entity is NOT
saved to the database - it's purely for optimization purposes.
"""

from typing import List
from dataclasses import dataclass

from src.domain.entities.factor.factor import Factor


@dataclass
class FactorSerieCollection:
    """
    Domain entity representing a collection of factor entities for optimization.
    
    This class encapsulates a list of factor entities to optimize
    factor value creation and database population operations.
    NOT saved to database - purely for optimization.
    """
    factors: List[Factor]
    
    def __post_init__(self):
        """Validate factor collection."""
        if not isinstance(self.factors, list):
            raise ValueError("factors must be a list")
        
        if not self.factors:
            raise ValueError("factors list cannot be empty")
        
        # Ensure all items are Factor instances
        for factor in self.factors:
            if not isinstance(factor, Factor):
                raise ValueError("All items in factors list must be Factor instances")
    
    def get_factor_by_name(self, name: str) -> Factor:
        """Get factor by name from the collection."""
        for factor in self.factors:
            if factor.name == name:
                return factor
        return None
    
    def get_factors_by_group(self, group: str) -> List[Factor]:
        """Get all factors in a specific group."""
        return [factor for factor in self.factors if factor.group == group]
    
    def get_factors_by_subgroup(self, subgroup: str) -> List[Factor]:
        """Get all factors in a specific subgroup."""
        return [factor for factor in self.factors if factor.subgroup == subgroup]
    
    def get_factor_ids(self) -> List[int]:
        """Get all factor IDs from the collection."""
        return [factor.id for factor in self.factors if factor.id is not None]
    
    def get_factor_names(self) -> List[str]:
        """Get all factor names from the collection."""
        return [factor.name for factor in self.factors]
    
    def add_factor(self, factor: Factor) -> None:
        """Add a factor to the collection."""
        if not isinstance(factor, Factor):
            raise ValueError("factor must be a Factor instance")
        
        # Check for duplicates by name
        existing = self.get_factor_by_name(factor.name)
        if existing:
            raise ValueError(f"Factor with name '{factor.name}' already exists in collection")
        
        self.factors.append(factor)
    
    def remove_factor_by_name(self, name: str) -> bool:
        """Remove a factor from the collection by name."""
        for i, factor in enumerate(self.factors):
            if factor.name == name:
                del self.factors[i]
                return True
        return False
    
    def __len__(self) -> int:
        """Return the number of factors in the collection."""
        return len(self.factors)
    
    def __iter__(self):
        """Make the collection iterable."""
        return iter(self.factors)