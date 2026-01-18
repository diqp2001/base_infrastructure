"""
Mapper for CompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with factor integration for historical price data.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from src.domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare as DomainCompanyShare
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel as ORMCompanyShare



class CompanyShareMapper:
    """Mapper for CompanyShare domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCompanyShare) -> DomainCompanyShare:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCompanyShare(
            id=orm_obj.id,
            ticker=orm_obj.ticker,
            exchange_id=orm_obj.exchange_id,
            company_id=orm_obj.company_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )
        
        # Set market data if available
        if orm_obj.current_price:
            market_data = MarketData(
                timestamp=orm_obj.last_update or datetime.now(),
                price=Decimal(str(orm_obj.current_price)),
                volume=None
            )
            domain_entity.update_market_data(market_data)
        
        # Fundamental data mapping removed - use factors instead
        
        # Set basic properties only (company_name field removed)
        if hasattr(orm_obj, 'sector'):
            domain_entity.set_sector(getattr(orm_obj, 'sector', None))
        if hasattr(orm_obj, 'industry'):
            domain_entity.set_industry(getattr(orm_obj, 'industry', None))
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCompanyShare, orm_obj: Optional[ORMCompanyShare] = None) -> ORMCompanyShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCompanyShare()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.ticker = domain_obj.ticker
        orm_obj.exchange_id = domain_obj.exchange_id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Map market data
        orm_obj.current_price = domain_obj.price
        orm_obj.last_update = domain_obj.last_update
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        # Fundamental data mapping removed - use factors instead
        
        # Only map basic properties (fundamental fields and company_name removed)
        
        return orm_obj



