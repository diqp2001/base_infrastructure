"""
FactorBatch DTO for batch operations on Factor entities.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.domain.entities.factor.factor import Factor


@dataclass
class FactorBatch:
    """
    Data Transfer Object for batch operations on Factor entities.
    
    Used for optimizing factor creation and bulk operations without
    persisting the batch itself to the database.
    """
    factors: List[Factor]
    batch_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate batch constraints."""
        if not self.factors:
            raise ValueError("factors list cannot be empty")
        
        if self.batch_size is None:
            self.batch_size = len(self.factors)
        elif self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
            
        if self.metadata is None:
            self.metadata = {}
    
    def add_factor(self, factor: Factor) -> None:
        """Add a factor to the batch."""
        self.factors.append(factor)
        self.batch_size = len(self.factors)
    
    def get_factors_by_group(self, group: str) -> List[Factor]:
        """Get factors filtered by group."""
        return [f for f in self.factors if f.group == group]
    
    def get_factors_by_subgroup(self, subgroup: str) -> List[Factor]:
        """Get factors filtered by subgroup."""
        return [f for f in self.factors if f.subgroup == subgroup]
    
    def get_factor_names(self) -> List[str]:
        """Get list of all factor names in the batch."""
        return [f.name for f in self.factors]
    
    def size(self) -> int:
        """Get the number of factors in the batch."""
        return len(self.factors)
    
    def is_empty(self) -> bool:
        """Check if the batch is empty."""
        return len(self.factors) == 0
    
    def chunk(self, chunk_size: int) -> List['FactorBatch']:
        """Split the batch into smaller chunks."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        
        chunks = []
        for i in range(0, len(self.factors), chunk_size):
            chunk_factors = self.factors[i:i + chunk_size]
            chunk_metadata = self.metadata.copy() if self.metadata else {}
            chunk_metadata['chunk_index'] = i // chunk_size
            chunk_metadata['original_batch_size'] = len(self.factors)
            
            chunks.append(FactorBatch(
                factors=chunk_factors,
                batch_size=len(chunk_factors),
                metadata=chunk_metadata
            ))
        
        return chunks
    
    def __len__(self) -> int:
        """Return the number of factors in the batch."""
        return len(self.factors)
    
    def __iter__(self):
        """Allow iteration over factors."""
        return iter(self.factors)
    
    def __str__(self) -> str:
        return f"FactorBatch(size={len(self.factors)}, batch_size={self.batch_size})"