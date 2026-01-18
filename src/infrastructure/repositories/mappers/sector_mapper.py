"""
Mapper for Sector domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.sector import Sector as DomainSector
from src.infrastructure.models.sector import SectorModel as ORMSector


class SectorMapper:
    """Mapper for Sector domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMSector) -> DomainSector:
        """Convert ORM model to domain entity."""
        # Create domain entity with correct constructor parameters: (id, name, description)
        domain_entity = DomainSector(
            id=orm_obj.id,
            name=orm_obj.name,
            description=getattr(orm_obj, 'description', '')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainSector, orm_obj: Optional[ORMSector] = None) -> ORMSector:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            # Create ORM object with required parameters: (name, description)
            orm_obj = ORMSector(
                name=domain_obj.name,
                description=domain_obj.description
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'code') and hasattr(orm_obj, 'code'):
            orm_obj.code = domain_obj.code
        if hasattr(domain_obj, 'description') and hasattr(orm_obj, 'description'):
            orm_obj.description = domain_obj.description
        if hasattr(domain_obj, 'classification_system') and hasattr(orm_obj, 'classification_system'):
            orm_obj.classification_system = domain_obj.classification_system
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        # Set active status if it exists on the model
        if hasattr(orm_obj, 'is_active') and orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj