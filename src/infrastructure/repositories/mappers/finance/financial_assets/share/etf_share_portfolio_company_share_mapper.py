"""
Mapper for ETFSharePortfolioCompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.share.etf_share_portfolio_company_share import ETFSharePortfolioCompanyShare as DomainETFSharePortfolioCompanyShare
from src.infrastructure.models.finance.financial_assets.etf_share_portfolio_company_share import ETFSharePortfolioCompanyShareModel as ORMETFSharePortfolioCompanyShare


class ETFSharePortfolioCompanyShareMapper:
    """Mapper for ETFSharePortfolioCompanyShare domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMETFSharePortfolioCompanyShare) -> DomainETFSharePortfolioCompanyShare:
        """Convert ORM model to domain entity."""
        domain_entity = DomainETFSharePortfolioCompanyShare(
            id=orm_obj.id,
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            exchange_id=getattr(orm_obj, 'exchange_id', None),
            currency_id=getattr(orm_obj, 'currency_id', None),
            underlying_asset_id=getattr(orm_obj, 'underlying_asset_id', None),
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None)
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainETFSharePortfolioCompanyShare, orm_obj: Optional[ORMETFSharePortfolioCompanyShare] = None) -> ORMETFSharePortfolioCompanyShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMETFSharePortfolioCompanyShare()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        
        # Map ETF share portfolio company share specific fields
        if hasattr(domain_obj, 'exchange_id'):
            orm_obj.exchange_id = domain_obj.exchange_id
        if hasattr(domain_obj, 'currency_id'):
            orm_obj.currency_id = domain_obj.currency_id
        if hasattr(domain_obj, 'underlying_asset_id'):
            orm_obj.underlying_asset_id = domain_obj.underlying_asset_id
        
        # Map optional financial asset attributes
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'start_date'):
            orm_obj.start_date = domain_obj.start_date
        if hasattr(domain_obj, 'end_date'):
            orm_obj.end_date = domain_obj.end_date
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj