"""
Mapper for Portfolio domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.portfolio.portfolio import Portfolio as DomainPortfolio
from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel as ORMPortfolio


class PortfolioMapper:
    """Mapper for Portfolio domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPortfolio) -> DomainPortfolio:
        """Convert ORM model to domain entity."""
        return DomainPortfolio(
            id=orm_obj.id,
            name=orm_obj.name,
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None)
        )

    @staticmethod
    def to_orm(domain_obj: DomainPortfolio, orm_obj: Optional[ORMPortfolio] = None) -> ORMPortfolio:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPortfolio(
                name=domain_obj.name,
                description=getattr(domain_obj, 'description', None),
                portfolio_type=getattr(domain_obj, 'portfolio_type', 'STANDARD'),
                backtest_id=getattr(domain_obj, 'backtest_id', None)
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Map optional attributes if they exist in domain
        if hasattr(domain_obj, 'description'):
            orm_obj.description = domain_obj.description
        if hasattr(domain_obj, 'portfolio_type'):
            orm_obj.portfolio_type = domain_obj.portfolio_type
        if hasattr(domain_obj, 'backtest_id'):
            orm_obj.backtest_id = domain_obj.backtest_id
            
        return orm_obj