"""
Mapper for PortfolioCompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio as DomainPortfolioCompanyShare
from src.infrastructure.models.finance.portfolio.portfolio_company_share import CompanySharePortfolioModel as ORMPortfolioCompanyShare


class CompanySharePortfolioMapper:
    """Mapper for PortfolioCompanyShare domain entity and ORM model."""
    @property
    def discriminator(self):
        return "company_share_portfolio"
    @property
    def entity_class(self):
        return DomainPortfolioCompanyShare
    @property
    def model_class(self):
        return ORMPortfolioCompanyShare
    
    def to_domain(self, orm_obj: ORMPortfolioCompanyShare) -> DomainPortfolioCompanyShare:
        """Convert ORM model to domain entity."""
        return self.entity_class(
            id=orm_obj.id,
            name=orm_obj.name,
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None)
        )

    
    def to_orm(self,domain_obj: DomainPortfolioCompanyShare, orm_obj: Optional[ORMPortfolioCompanyShare] = None) -> ORMPortfolioCompanyShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = self.model_class(
                name=domain_obj.name,
                start_date=getattr(domain_obj, 'start_date', None),
            end_date=getattr(domain_obj, 'end_date', None)
                
            )
        
        
            
        return orm_obj