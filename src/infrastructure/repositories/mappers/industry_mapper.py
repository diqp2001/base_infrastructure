"""
Mapper for Industry domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.industry import Industry as DomainIndustry
from src.infrastructure.models.industry import Industry as ORMIndustry


class IndustryMapper:
    """Mapper for Industry domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMIndustry) -> DomainIndustry:
        """Convert ORM model to domain entity."""
        # Create domain entity with all available attributes
        domain_entity = DomainIndustry(
            id=orm_obj.id,
            name=orm_obj.name,
            code=getattr(orm_obj, 'code', None),
            sector_name=getattr(orm_obj, 'sector_name', None),
            sector_code=getattr(orm_obj, 'sector_code', None),
            description=getattr(orm_obj, 'description', None),
            classification_system=getattr(orm_obj, 'classification_system', 'GICS')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainIndustry, orm_obj: Optional[ORMIndustry] = None) -> ORMIndustry:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMIndustry()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'code') and hasattr(orm_obj, 'code'):
            orm_obj.code = domain_obj.code
        if hasattr(domain_obj, 'sector_name') and hasattr(orm_obj, 'sector_name'):
            orm_obj.sector_name = domain_obj.sector_name
        if hasattr(domain_obj, 'sector_code') and hasattr(orm_obj, 'sector_code'):
            orm_obj.sector_code = domain_obj.sector_code
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