"""
Mapper for PortfolioDerivative domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.portfolio.derivative_portfolio import DerivativePortfolio as DomainPortfolioDerivative
from src.infrastructure.models.finance.portfolio.portfolio_derivative import DerivativePortfolioModel as ORMPortfolioDerivative


class DerivativePortfolioMapper:
    """Mapper for PortfolioDerivative domain entity and ORM model."""

    @property
    def discriminator(self):
        return "derivative_portfolio"
    @property
    def entity_class(self):
        return DomainPortfolioDerivative
    @property
    def model_class(self):
        return ORMPortfolioDerivative

    def get_entity(self):
        return DomainPortfolioDerivative

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
                start_date=getattr(domain_obj, 'start_date', None),
            end_date=getattr(domain_obj, 'end_date', None)
                
            )
        
        
            
        return orm_obj