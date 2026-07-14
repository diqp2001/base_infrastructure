"""
Mapper for CompanySharePortfolioOptionPortfolio domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolio as DomainCompanySharePortfolioOptionPortfolio
from src.infrastructure.models.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolioModel as ORMCompanySharePortfolioOptionPortfolio


class CompanySharePortfolioOptionPortfolioMapper:
    """Mapper for CompanySharePortfolioOptionPortfolio domain entity and ORM model."""

    @property
    def discriminator(self):
        return "CompanySharePortfolioOptionPortfolio"
    @property
    def entity_class(self):
        return DomainCompanySharePortfolioOptionPortfolio
    @property
    def model_class(self):
        return ORMCompanySharePortfolioOptionPortfolio

    def get_entity(self):
        return DomainCompanySharePortfolioOptionPortfolio

    def to_domain(self,orm_obj):
        """Convert ORM model to domain entity."""
        return self.entity_class(
            id=orm_obj.id,
            name=orm_obj.name,
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None)
        )

    def to_orm(self,domain_obj, orm_obj = None):
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = self.model_class(
                name=domain_obj.name,
                portfolio_type=self.discriminator,
                start_date=getattr(domain_obj, 'start_date', None),
            end_date=getattr(domain_obj, 'end_date', None)
                
            )
        
        
            
        return orm_obj