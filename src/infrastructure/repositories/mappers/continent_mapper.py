"""
Mapper for Continent domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.continent import Continent as DomainContinent
from src.infrastructure.models.continent import ContinentModel as ORMContinent


class ContinentMapper:
    """Mapper for Continent domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMContinent) -> DomainContinent:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainContinent(
            id=orm_obj.id,
            name=orm_obj.name
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainContinent, orm_obj: Optional[ORMContinent] = None) -> ORMContinent:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMContinent()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        
        
        # Set timestamps
        if not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        orm_obj.updated_at = datetime.now()
        
        # Set active status
        if orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj