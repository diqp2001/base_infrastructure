"""
Domain entity for FactorValue.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.entity import Entity


@dataclass
class FactorValue:
    """
    Domain entity representing a factor value.
    Pure domain object without infrastructure concerns.

    entity refers to the associated Entity object (may be None for DB-loaded values).
    entity_type is the class name of the entity (e.g. 'Country', 'CompanyShare') used
    to discriminate between entities with the same numeric id across different tables.
    entity_id is the raw integer id, synced from entity.id when entity is provided.
    """
    id: Optional[int]
    factor_id: int
    entity: Optional['Entity']
    date: datetime
    value: str
    entity_type: Optional[str] = None   # Discriminator: entity class name
    entity_id: Optional[int] = None     # Raw id – synced from entity.id if entity provided

    def __post_init__(self):
        """Validate domain constraints and sync entity_id / entity_type from entity."""
        if self.factor_id <= 0:
            raise ValueError("factor_id must be positive")

        if self.entity is not None:
            # Sync entity_id from entity when entity object is available
            if self.entity_id is None:
                self.entity_id = self.entity.id
            # Auto-derive entity_type from entity's class name when not provided
            if self.entity_type is None:
                self.entity_type = type(self.entity).__name__

        if self.entity_id is not None and self.entity_id <= 0:
            raise ValueError("entity_id must be positive")

    def __str__(self) -> str:
        return (
            f"FactorValue(factor_id={self.factor_id}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id}, "
            f"date={self.date}, value={self.value})"
        )
