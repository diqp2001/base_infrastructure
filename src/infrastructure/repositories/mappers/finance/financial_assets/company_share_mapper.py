"""
Mapper for CompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.entities.finance.financial_assets.company_share import CompanyShare as DomainCompanyShare
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare as ORMCompanyShare
from src.domain.entities.finance.financial_assets.security import Symbol, SecurityType, MarketData
from src.domain.entities.finance.financial_assets.equity import FundamentalData


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
        
        # Set fundamental data if available
        if orm_obj.market_cap or orm_obj.pe_ratio:
            fundamentals = FundamentalData(
                market_cap=Decimal(str(orm_obj.market_cap)) if orm_obj.market_cap else None,
                shares_outstanding=float(orm_obj.shares_outstanding) if orm_obj.shares_outstanding else None,
                pe_ratio=Decimal(str(orm_obj.pe_ratio)) if orm_obj.pe_ratio else None,
                dividend_yield=Decimal(str(orm_obj.dividend_yield)) if orm_obj.dividend_yield else None,
                book_value_per_share=Decimal(str(orm_obj.book_value_per_share)) if orm_obj.book_value_per_share else None,
                earnings_per_share=Decimal(str(orm_obj.earnings_per_share)) if orm_obj.earnings_per_share else None
            )
            domain_entity.update_fundamentals(fundamentals)
        
        # Set additional properties
        if orm_obj.sector:
            domain_entity.set_sector(orm_obj.sector)
        if orm_obj.industry:
            domain_entity.set_industry(orm_obj.industry)
        
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
        
        # Map fundamental data
        if domain_obj.fundamentals:
            orm_obj.market_cap = domain_obj.fundamentals.market_cap
            orm_obj.shares_outstanding = domain_obj.fundamentals.shares_outstanding
            orm_obj.pe_ratio = domain_obj.fundamentals.pe_ratio
            orm_obj.dividend_yield = domain_obj.fundamentals.dividend_yield
            orm_obj.book_value_per_share = domain_obj.fundamentals.book_value_per_share
            orm_obj.earnings_per_share = domain_obj.fundamentals.earnings_per_share
        
        # Map additional properties
        orm_obj.sector = domain_obj.sector
        orm_obj.industry = domain_obj.industry
        
        return orm_obj


