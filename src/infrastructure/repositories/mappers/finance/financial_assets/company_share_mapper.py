"""
Mapper for CompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with factor integration for historical price data.
Enhanced with get_or_create functionality for related models.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare as DomainCompanyShare
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel as ORMCompanyShare



class CompanyShareMapper:
    """Mapper for CompanyShare domain entity and ORM model."""
    @property
    def discriminator(self):
        return 'company_share'
    @property
    def entity_class(self):
        """Return the domain entity class for Currency."""
        return DomainCompanyShare
    @property
    def model_class(self):
        return ORMCompanyShare

    @staticmethod
    def to_domain(orm_obj: ORMCompanyShare) -> DomainCompanyShare:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCompanyShare(
            id=orm_obj.id,
            symbol=orm_obj.symbol,
            exchange_id=orm_obj.exchange_id,
            company_id=orm_obj.company_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )
        
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCompanyShare, orm_obj: Optional[ORMCompanyShare] = None) -> ORMCompanyShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCompanyShare()
        
        # Map basic fields
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.exchange_id = domain_obj.exchange_id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        
        
    
        
        return orm_obj
    



