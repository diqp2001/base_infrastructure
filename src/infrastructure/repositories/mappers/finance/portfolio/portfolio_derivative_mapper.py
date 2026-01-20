"""
Mapper for PortfolioDerivative domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.portfolio.portfolio_derivative import PortfolioDerivative as DomainPortfolioDerivative
from src.infrastructure.models.finance.portfolio.portfolio_derivative import PortfolioDerivativeModel as ORMPortfolioDerivative


class PortfolioDerivativeMapper:
    """Mapper for PortfolioDerivative domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPortfolioDerivative) -> DomainPortfolioDerivative:
        """Convert ORM model to domain entity."""
        domain_entity = DomainPortfolioDerivative(
            id=orm_obj.id,
            name=orm_obj.name
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainPortfolioDerivative, orm_obj: Optional[ORMPortfolioDerivative] = None) -> ORMPortfolioDerivative:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPortfolioDerivative()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj