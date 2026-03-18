"""
ETFSharePortfolioCompanyShare Repository for local database operations.
Follows the same patterns as other repositories in the project.
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.domain.entities.finance.financial_assets.share.etf_share_portfolio_company_share import ETFSharePortfolioCompanyShare as DomainETFSharePortfolioCompanyShare
from src.infrastructure.models.finance.financial_assets.etf_share_portfolio_company_share import ETFSharePortfolioCompanyShareModel as ORMETFSharePortfolioCompanyShare
from src.infrastructure.repositories.mappers.finance.financial_assets.etf_share_portfolio_company_share_mapper import ETFSharePortfolioCompanyShareMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.domain.ports.finance.financial_assets.etf_share_portfolio_company_share_port import ETFSharePortfolioCompanySharePort

logger = logging.getLogger(__name__)


class ETFSharePortfolioCompanyShareRepository(ShareRepository, ETFSharePortfolioCompanySharePort):
    """Repository for ETF share portfolio company share operations in the local database."""

    def __init__(self, session: Session, factory):
        """Initialize ETFSharePortfolioCompanyShareRepository with database session."""
        super().__init__(session, factory)
        self.mapper = ETFSharePortfolioCompanyShareMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for ETFSharePortfolioCompanyShares."""
        return ORMETFSharePortfolioCompanyShare
    
    @property
    def entity_class(self):
        """Return the domain entity class for ETFSharePortfolioCompanyShares."""
        return DomainETFSharePortfolioCompanyShare

    def get_or_create(self, symbol: str = None, name: str = None, 
                      exchange_id: int = None, currency_code: str = "USD", 
                      underlying_asset_id: int = None) -> Optional[DomainETFSharePortfolioCompanyShare]:
        """
        Get or create an ETF share portfolio company share with dependency resolution.
        
        Args:
            symbol: Share symbol
            name: Share name (optional)
            exchange_id: Required exchange ID
            currency_code: Currency ISO code (default: USD)
            underlying_asset_id: Optional underlying asset ID
            
        Returns:
            Domain ETF share portfolio company share entity or None if creation failed
        """
        try:
            # First try to get existing share by symbol
            if symbol:
                existing = self.get_by_symbol(symbol)
                if existing:
                    return existing
            
            # Validate exchange exists if provided
            if exchange_id:
                from src.infrastructure.models.finance.exchange import ExchangeModel
                exchange_exists = self.session.query(ExchangeModel).filter(
                    ExchangeModel.id == exchange_id
                ).first()
                
                if not exchange_exists:
                    logger.error(f"Exchange with ID {exchange_id} does not exist")
                    return None
            
            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency = currency_local_repo.get_or_create(iso_code=currency_code)
            
            # Create new ETF share portfolio company share
            new_share = DomainETFSharePortfolioCompanyShare(
                id=None,
                name=name or f"ETF Share Portfolio Company Share {symbol}",
                symbol=symbol,
                exchange_id=exchange_id,
                currency_id=currency.asset_id if currency else None,
                underlying_asset_id=underlying_asset_id
            )
            
            return self.add(new_share)
            
        except Exception as e:
            logger.error(f"Error in get_or_create for ETF share portfolio company share {symbol}: {e}")
            return None

    def get_by_exchange_id(self, exchange_id: int) -> List[DomainETFSharePortfolioCompanyShare]:
        """
        Retrieve ETF share portfolio company shares by exchange ID.
        
        Args:
            exchange_id: ID of the exchange
            
        Returns:
            List of domain ETF share portfolio company share entities
        """
        try:
            orm_shares = self.session.query(ORMETFSharePortfolioCompanyShare).filter(
                ORMETFSharePortfolioCompanyShare.exchange_id == exchange_id
            ).all()
            
            return [self.mapper.to_domain(orm_share) for orm_share in orm_shares]
            
        except Exception as e:
            logger.error(f"Error retrieving ETF share portfolio company shares by exchange ID {exchange_id}: {e}")
            raise

    def get_by_currency_id(self, currency_id: int) -> List[DomainETFSharePortfolioCompanyShare]:
        """
        Retrieve ETF share portfolio company shares by currency ID.
        
        Args:
            currency_id: ID of the currency
            
        Returns:
            List of domain ETF share portfolio company share entities
        """
        try:
            orm_shares = self.session.query(ORMETFSharePortfolioCompanyShare).filter(
                ORMETFSharePortfolioCompanyShare.currency_id == currency_id
            ).all()
            
            return [self.mapper.to_domain(orm_share) for orm_share in orm_shares]
            
        except Exception as e:
            logger.error(f"Error retrieving ETF share portfolio company shares by currency ID {currency_id}: {e}")
            raise

    def get_by_underlying_asset_id(self, underlying_asset_id: int) -> List[DomainETFSharePortfolioCompanyShare]:
        """
        Retrieve ETF share portfolio company shares by underlying asset ID.
        
        Args:
            underlying_asset_id: ID of the underlying asset
            
        Returns:
            List of domain ETF share portfolio company share entities
        """
        try:
            orm_shares = self.session.query(ORMETFSharePortfolioCompanyShare).filter(
                ORMETFSharePortfolioCompanyShare.underlying_asset_id == underlying_asset_id
            ).all()
            
            return [self.mapper.to_domain(orm_share) for orm_share in orm_shares]
            
        except Exception as e:
            logger.error(f"Error retrieving ETF share portfolio company shares by underlying asset ID {underlying_asset_id}: {e}")
            raise

    def get_by_symbol(self, symbol: str) -> Optional[DomainETFSharePortfolioCompanyShare]:
        """Get ETF share portfolio company share by symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.symbol == symbol
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            logger.error(f"Error retrieving ETF share portfolio company share by symbol {symbol}: {e}")
            return None