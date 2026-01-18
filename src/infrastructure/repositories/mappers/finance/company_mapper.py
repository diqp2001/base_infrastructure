"""
Mapper for Company domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.company import Company as DomainCompany
from src.infrastructure.models.finance.company import CompanyModel as ORMCompany


class CompanyMapper:
    """Mapper for Company domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCompany) -> DomainCompany:
        """Convert ORM model to domain entity."""
        # Create domain entity with correct constructor parameters: (id, name, legal_name, country_id, industry_id, start_date, end_date)
        domain_entity = DomainCompany(
            id=orm_obj.id,
            name=orm_obj.name,
            legal_name=orm_obj.legal_name,
            country_id=orm_obj.country_id,
            industry_id=orm_obj.industry_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCompany, orm_obj: Optional[ORMCompany] = None) -> ORMCompany:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            # Create ORM object with required parameters: (name, legal_name, country_id, industry_id, start_date, end_date)
            orm_obj = ORMCompany(
                name=domain_obj.name,
                legal_name=domain_obj.legal_name,
                country_id=domain_obj.country_id,
                industry_id=domain_obj.industry_id,
                start_date=domain_obj.start_date,
                end_date=domain_obj.end_date
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.legal_name = domain_obj.legal_name
        orm_obj.country_id = domain_obj.country_id
        orm_obj.industry_id = domain_obj.industry_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        return orm_obj