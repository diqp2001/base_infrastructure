"""
Mapper for PortfolioCompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare as DomainPortfolioCompanyShare
from src.infrastructure.models.finance.portfolio.portfolio_company_share import PortfolioCompanyShareModel as ORMPortfolioCompanyShare


class PortfolioCompanyShareMapper:
    """Mapper for PortfolioCompanyShare domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPortfolioCompanyShare) -> DomainPortfolioCompanyShare:
        """Convert ORM model to domain entity."""
        domain_entity = DomainPortfolioCompanyShare(
            id=orm_obj.id,
            name=orm_obj.name
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainPortfolioCompanyShare, orm_obj: Optional[ORMPortfolioCompanyShare] = None) -> ORMPortfolioCompanyShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPortfolioCompanyShare()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj