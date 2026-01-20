"""
Mapper for CompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with factor integration for historical price data.
Enhanced with get_or_create functionality for related models.
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
    
    @staticmethod
    def to_orm_with_dependencies(domain_obj: DomainCompanyShare, session, orm_obj: Optional[ORMCompanyShare] = None) -> ORMCompanyShare:
        """
        Convert domain entity to ORM model with get_or_create for dependencies.
        
        Args:
            domain_obj: Domain company share entity
            session: SQLAlchemy session for database operations
            orm_obj: Optional existing ORM object to update
            
        Returns:
            ORMCompanyShare: ORM model with resolved dependencies
        """
        if orm_obj is None:
            orm_obj = ORMCompanyShare()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.ticker = domain_obj.ticker
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Get or create company dependency
        if domain_obj.company_id:
            from src.infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
            try:
                company_repo = CompanyRepository(session)
                company = company_repo.get_by_id(domain_obj.company_id)
                if not company:
                    # Create a default company if not found
                    from src.domain.entities.finance.company import Company as DomainCompany
                    default_company = DomainCompany(
                        id=domain_obj.company_id,
                        name=f"Unknown Company ({domain_obj.ticker})",
                        country_id=1  # Default country
                    )
                    company = company_repo.add(default_company)
                orm_obj.company_id = company.id if company else domain_obj.company_id
            except ImportError:
                # If CompanyRepository not available, use the original value
                orm_obj.company_id = domain_obj.company_id
        
        # Get or create exchange dependency
        if domain_obj.exchange_id:
            from src.infrastructure.repositories.local_repo.finance.exchange_repository import ExchangeRepository
            try:
                exchange_repo = ExchangeRepository(session)
                exchange = exchange_repo.get_by_id(domain_obj.exchange_id)
                if not exchange:
                    # Create a default exchange if not found
                    from src.domain.entities.finance.exchange import Exchange as DomainExchange
                    default_exchange = DomainExchange(
                        id=domain_obj.exchange_id,
                        name=f"Unknown Exchange",
                        country_id=1  # Default country
                    )
                    exchange = exchange_repo.add(default_exchange)
                orm_obj.exchange_id = exchange.id if exchange else domain_obj.exchange_id
            except ImportError:
                # If ExchangeRepository not available, use the original value
                orm_obj.exchange_id = domain_obj.exchange_id
        
        # Map market data
        orm_obj.current_price = domain_obj.price
        orm_obj.last_update = domain_obj.last_update
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        return orm_obj



