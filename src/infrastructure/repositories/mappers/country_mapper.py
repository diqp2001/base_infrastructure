"""
Mapper for Country domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.country import Country as DomainCountry
from src.infrastructure.models.country import CountryModel as ORMCountry


class CountryMapper:
    """Mapper for Country domain entity and ORM model."""
    @property
    def entity_class(self):
        return DomainCountry
    @property
    def model_class(self):
        return ORMCountry
    def to_domain(self,orm_obj: ORMCountry) -> DomainCountry:
        """Convert ORM model to domain entity."""
        # Create domain entity with correct constructor parameters: (id, name, continent_id)
        domain_entity = self.entity_class(
            id=orm_obj.id,
            name=orm_obj.name,
            iso_code=orm_obj.iso_code,
            continent_id=orm_obj.continent_id
        )
        
        return domain_entity

    def to_orm(self,domain_obj: DomainCountry, orm_obj: Optional[ORMCountry] = None) -> ORMCountry:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            # Create ORM object with required parameters: (name, iso_code)
            orm_obj = self.model_class(
                name=domain_obj.name,
                iso_code=domain_obj.iso_code  # Default to 'US' if not set
            )
        
        # Only assign ID if explicitly set (avoid breaking autoincrement)
        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id

        orm_obj.name = domain_obj.name
        orm_obj.iso_code = domain_obj.iso_code
        orm_obj.continent_id = domain_obj.continent_id
        
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        # Set active status if it exists on the model
        if hasattr(orm_obj, 'is_active') and orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj