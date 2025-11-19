"""
Mapper for Country domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.country import Country as DomainCountry
from src.infrastructure.models.country import Country as ORMCountry


class CountryMapper:
    """Mapper for Country domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCountry) -> DomainCountry:
        """Convert ORM model to domain entity."""
        # Create domain entity with all available attributes
        domain_entity = DomainCountry(
            id=orm_obj.id,
            name=orm_obj.name,
            iso_code=getattr(orm_obj, 'iso_code', None),
            iso3_code=getattr(orm_obj, 'iso3_code', None),
            continent=getattr(orm_obj, 'continent', None),
            region=getattr(orm_obj, 'region', None),
            currency=getattr(orm_obj, 'currency', None),
            timezone=getattr(orm_obj, 'timezone', None),
            population=getattr(orm_obj, 'population', None)
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCountry, orm_obj: Optional[ORMCountry] = None) -> ORMCountry:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCountry()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'iso_code') and hasattr(orm_obj, 'iso_code'):
            orm_obj.iso_code = domain_obj.iso_code
        if hasattr(domain_obj, 'iso3_code') and hasattr(orm_obj, 'iso3_code'):
            orm_obj.iso3_code = domain_obj.iso3_code
        if hasattr(domain_obj, 'continent') and hasattr(orm_obj, 'continent'):
            orm_obj.continent = domain_obj.continent
        if hasattr(domain_obj, 'region') and hasattr(orm_obj, 'region'):
            orm_obj.region = domain_obj.region
        if hasattr(domain_obj, 'currency') and hasattr(orm_obj, 'currency'):
            orm_obj.currency = domain_obj.currency
        if hasattr(domain_obj, 'timezone') and hasattr(orm_obj, 'timezone'):
            orm_obj.timezone = domain_obj.timezone
        if hasattr(domain_obj, 'population') and hasattr(orm_obj, 'population'):
            orm_obj.population = domain_obj.population
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        # Set active status if it exists on the model
        if hasattr(orm_obj, 'is_active') and orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj