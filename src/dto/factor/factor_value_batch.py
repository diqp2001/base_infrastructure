"""
FactorValueBatch DTO for batch operations on FactorValue entities.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from src.domain.entities.factor.factor_value import FactorValue


@dataclass
class FactorValueBatch:
    """
    Data Transfer Object for batch operations on FactorValue entities.
    
    Used for optimizing factor value creation and bulk database operations
    without persisting the batch itself to the database.
    """
    factor_values: List[FactorValue]
    batch_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate batch constraints."""
        if not self.factor_values:
            raise ValueError("factor_values list cannot be empty")
        
        if self.batch_size is None:
            self.batch_size = len(self.factor_values)
        elif self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
            
        if self.metadata is None:
            self.metadata = {}
    
    def add_factor_value(self, factor_value: FactorValue) -> None:
        """Add a factor value to the batch."""
        self.factor_values.append(factor_value)
        self.batch_size = len(self.factor_values)
    
    def get_by_factor_id(self, factor_id: int) -> List[FactorValue]:
        """Get factor values filtered by factor ID."""
        return [fv for fv in self.factor_values if fv.factor_id == factor_id]
    
    def get_by_entity_id(self, entity_id: int) -> List[FactorValue]:
        """Get factor values filtered by entity ID."""
        return [fv for fv in self.factor_values if fv.entity_id == entity_id]
    
    def get_by_date(self, target_date: date) -> List[FactorValue]:
        """Get factor values for a specific date."""
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        return [fv for fv in self.factor_values if fv.date.date() == target_date]
    
    def get_by_date_range(self, start_date: date, end_date: date) -> List[FactorValue]:
        """Get factor values within a date range."""
        return [fv for fv in self.factor_values 
                if start_date <= fv.date.date() <= end_date]
    
    def get_unique_factor_ids(self) -> List[int]:
        """Get list of unique factor IDs in the batch."""
        return list(set(fv.factor_id for fv in self.factor_values))
    
    def get_unique_entity_ids(self) -> List[int]:
        """Get list of unique entity IDs in the batch."""
        return list(set(fv.entity_id for fv in self.factor_values))
    
    def get_unique_dates(self) -> List[date]:
        """Get list of unique dates in the batch."""
        return list(set(fv.date.date() for fv in self.factor_values))
    
    def group_by_factor_id(self) -> Dict[int, List[FactorValue]]:
        """Group factor values by factor ID."""
        grouped = {}
        for fv in self.factor_values:
            if fv.factor_id not in grouped:
                grouped[fv.factor_id] = []
            grouped[fv.factor_id].append(fv)
        return grouped
    
    def group_by_entity_id(self) -> Dict[int, List[FactorValue]]:
        """Group factor values by entity ID."""
        grouped = {}
        for fv in self.factor_values:
            if fv.entity_id not in grouped:
                grouped[fv.entity_id] = []
            grouped[fv.entity_id].append(fv)
        return grouped
    
    def group_by_date(self) -> Dict[date, List[FactorValue]]:
        """Group factor values by date."""
        grouped = {}
        for fv in self.factor_values:
            fv_date = fv.date.date()
            if fv_date not in grouped:
                grouped[fv_date] = []
            grouped[fv_date].append(fv)
        return grouped
    
    def sort_by_date(self, ascending: bool = True) -> None:
        """Sort factor values by date in-place."""
        self.factor_values.sort(key=lambda fv: fv.date, reverse=not ascending)
    
    def filter_duplicates(self) -> 'FactorValueBatch':
        """
        Create a new batch with duplicate factor values removed.
        Duplicates are defined as same factor_id, entity_id, and date.
        """
        seen = set()
        unique_values = []
        
        for fv in self.factor_values:
            key = (fv.factor_id, fv.entity_id, fv.date)
            if key not in seen:
                seen.add(key)
                unique_values.append(fv)
        
        return FactorValueBatch(
            factor_values=unique_values,
            metadata={**self.metadata, 'filtered_duplicates': True}
        )
    
    def chunk(self, chunk_size: int) -> List['FactorValueBatch']:
        """Split the batch into smaller chunks."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        
        chunks = []
        for i in range(0, len(self.factor_values), chunk_size):
            chunk_values = self.factor_values[i:i + chunk_size]
            chunk_metadata = self.metadata.copy() if self.metadata else {}
            chunk_metadata['chunk_index'] = i // chunk_size
            chunk_metadata['original_batch_size'] = len(self.factor_values)
            
            chunks.append(FactorValueBatch(
                factor_values=chunk_values,
                batch_size=len(chunk_values),
                metadata=chunk_metadata
            ))
        
        return chunks
    
    def size(self) -> int:
        """Get the number of factor values in the batch."""
        return len(self.factor_values)
    
    def is_empty(self) -> bool:
        """Check if the batch is empty."""
        return len(self.factor_values) == 0
    
    def __len__(self) -> int:
        """Return the number of factor values in the batch."""
        return len(self.factor_values)
    
    def __iter__(self):
        """Allow iteration over factor values."""
        return iter(self.factor_values)
    
    def __str__(self) -> str:
        return f"FactorValueBatch(size={len(self.factor_values)}, batch_size={self.batch_size})"