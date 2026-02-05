"""
Factor Value Collection domain entity for optimization.

This entity contains a list of factor value entities and is used to optimize
factor value creation/population in the database. This entity is NOT
saved to the database - it's purely for optimization purposes.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.factor.factor_value import FactorValue


@dataclass
class FactorValueCollection:
    """
    Domain entity representing a collection of factor values for optimization.
    
    This class encapsulates a list of factor value entities to optimize
    bulk database population operations. NOT saved to database - purely 
    for optimization.
    """
    factor_values: List[FactorValue]
    
    def __post_init__(self):
        """Validate factor value collection."""
        if not isinstance(self.factor_values, list):
            raise ValueError("factor_values must be a list")
        
        if not self.factor_values:
            raise ValueError("factor_values list cannot be empty")
        
        # Ensure all items are FactorValue instances
        for factor_value in self.factor_values:
            if not isinstance(factor_value, FactorValue):
                raise ValueError("All items in factor_values list must be FactorValue instances")
    
    def get_values_by_factor_id(self, factor_id: int) -> List[FactorValue]:
        """Get all factor values for a specific factor ID."""
        return [fv for fv in self.factor_values if fv.factor_id == factor_id]
    
    def get_values_by_entity_id(self, entity_id: int) -> List[FactorValue]:
        """Get all factor values for a specific entity ID."""
        return [fv for fv in self.factor_values if fv.entity_id == entity_id]
    
    def get_values_by_factor_and_entity(self, factor_id: int, entity_id: int) -> List[FactorValue]:
        """Get all factor values for a specific factor and entity combination."""
        return [fv for fv in self.factor_values 
                if fv.factor_id == factor_id and fv.entity_id == entity_id]
    
    def get_values_by_date(self, date: datetime) -> List[FactorValue]:
        """Get all factor values for a specific date."""
        return [fv for fv in self.factor_values if fv.date.date() == date.date()]
    
    def get_unique_factor_ids(self) -> List[int]:
        """Get unique factor IDs from the collection."""
        return list(set(fv.factor_id for fv in self.factor_values))
    
    def get_unique_entity_ids(self) -> List[int]:
        """Get unique entity IDs from the collection."""
        return list(set(fv.entity_id for fv in self.factor_values))
    
    def get_unique_dates(self) -> List[datetime]:
        """Get unique dates from the collection."""
        return list(set(fv.date for fv in self.factor_values))
    
    def add_factor_value(self, factor_value: FactorValue) -> None:
        """Add a factor value to the collection."""
        if not isinstance(factor_value, FactorValue):
            raise ValueError("factor_value must be a FactorValue instance")
        
        # Check for duplicates by factor_id, entity_id, and date
        existing = self.get_value_by_composite_key(
            factor_value.factor_id, 
            factor_value.entity_id, 
            factor_value.date
        )
        if existing:
            raise ValueError(f"FactorValue with factor_id={factor_value.factor_id}, "
                           f"entity_id={factor_value.entity_id}, date={factor_value.date} "
                           f"already exists in collection")
        
        self.factor_values.append(factor_value)
    
    def get_value_by_composite_key(self, factor_id: int, entity_id: int, date: datetime) -> Optional[FactorValue]:
        """Get factor value by composite key (factor_id, entity_id, date)."""
        for fv in self.factor_values:
            if (fv.factor_id == factor_id and 
                fv.entity_id == entity_id and 
                fv.date.date() == date.date()):
                return fv
        return None
    
    def remove_factor_value(self, factor_id: int, entity_id: int, date: datetime) -> bool:
        """Remove a factor value from the collection by composite key."""
        for i, fv in enumerate(self.factor_values):
            if (fv.factor_id == factor_id and 
                fv.entity_id == entity_id and 
                fv.date.date() == date.date()):
                del self.factor_values[i]
                return True
        return False
    
    def get_batch_size(self) -> int:
        """Get the number of factor values in the collection for batch processing."""
        return len(self.factor_values)
    
    def split_by_factor_id(self) -> dict:
        """Split collection into sub-collections grouped by factor_id."""
        factor_groups = {}
        for factor_value in self.factor_values:
            factor_id = factor_value.factor_id
            if factor_id not in factor_groups:
                factor_groups[factor_id] = []
            factor_groups[factor_id].append(factor_value)
        
        return {
            factor_id: FactorValueCollection(values) 
            for factor_id, values in factor_groups.items()
        }
    
    def __len__(self) -> int:
        """Return the number of factor values in the collection."""
        return len(self.factor_values)
    
    def __iter__(self):
        """Make the collection iterable."""
        return iter(self.factor_values)