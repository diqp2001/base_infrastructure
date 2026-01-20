"""
Options Repository for local database operations.
Follows the same patterns as other repositories in the project.
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.domain.entities.finance.financial_assets.options import Options as DomainOptions
from src.infrastructure.models.finance.financial_assets.derivative.options import OptionsModel as ORMOptions
from src.infrastructure.repositories.mappers.finance.financial_assets.options_mapper import OptionsMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.derivatives_repository import DerivativesRepository

logger = logging.getLogger(__name__)


class OptionsRepository(DerivativesRepository):
    def __init__(self, session: Session):
        """Initialize the repository with a database session."""
        super().__init__(session)
        self.mapper = OptionsMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Options."""
        return ORMOptions
    
    @property
    def entity_class(self):
        """Return the domain entity class for Options."""
        return DomainOptions

    def get_or_create(self, ticker: str = None, name: str = None, symbol: str = None, 
                      currency_code: str = "USD", option_type: str = None, 
                      underlying_asset_id: int = None) -> Optional[DomainOptions]:
        """
        Get or create an options with dependency resolution.
        Integrates the functionality from to_orm_with_dependencies.
        
        Args:
            ticker: Options ticker (optional)
            name: Options name (optional)
            symbol: Options symbol (optional) 
            currency_code: Currency ISO code (default: USD)
            option_type: Type of option (CALL/PUT)
            underlying_asset_id: Required ID of the underlying asset
            
        Returns:
            Domain options entity or None if creation failed
        """
        try:
            # First try to get existing option by ticker or symbol
            if ticker:
                existing = self.get_by_ticker(ticker)
                if existing:
                    return existing
            elif symbol:
                existing = self.get_by_symbol(symbol)
                if existing:
                    return existing
            
            # Validate underlying asset exists if provided
            if underlying_asset_id:
                from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
                # Query to check if underlying asset exists
                underlying_exists = self.session.query(FinancialAssetModel).filter(
                    FinancialAssetModel.id == underlying_asset_id
                ).first()
                
                if not underlying_exists:
                    logger.error(f"Underlying asset with ID {underlying_asset_id} does not exist")
                    return None
            
            # Get or create currency dependency
            from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
            currency_repo = CurrencyRepository(self.session)
            currency = currency_repo.get_or_create(iso_code=currency_code)
            
            # Create new option
            new_option = DomainOptions(
                ticker=ticker or f"OPTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=name or f"Option {ticker or symbol}",
                symbol=symbol or ticker,
                option_type=option_type or "CALL"
            )
            
            # Set currency_id if the model supports it
            if hasattr(new_option, 'currency_id') and currency:
                new_option.currency_id = currency.asset_id
            
            # Set underlying_asset_id if provided
            if hasattr(new_option, 'underlying_asset_id') and underlying_asset_id:
                new_option.underlying_asset_id = underlying_asset_id
            
            return self.add(new_option)
            
        except Exception as e:
            logger.error(f"Error in get_or_create for option {ticker or symbol}: {e}")
            return None

    def add(self, option: DomainOptions) -> DomainOptions:
        """
        Add a single option to the database.
        
        :param option: Domain option entity to add
        :return: The saved option entity with assigned ID
        :raises: IntegrityError if option already exists
        """
        try:
            # Convert domain entity to ORM model
            orm_option = self.mapper.to_orm(option)
            
            # Add to session and flush to get the ID
            self.session.add(orm_option)
            self.session.flush()
            
            self.session.commit()
            
            logger.info(f"Added option: {option.ticker} with ID {orm_option.id}")
            
            # Update domain entity with assigned ID and return
            option.id = orm_option.id
            return option
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Option {option.ticker} already exists: {e}")
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding option {option.ticker}: {e}")
            raise

    def get_by_ticker(self, ticker: str) -> Optional[DomainOptions]:
        """
        Retrieve an option by its ticker.
        
        :param ticker: Ticker symbol
        :return: Domain option entity or None if not found
        """
        try:
            orm_option = self.session.query(ORMOptions).filter(
                ORMOptions.ticker == ticker
            ).first()
            
            if orm_option:
                return self.mapper.to_domain(orm_option)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving option by ticker {ticker}: {e}")
            raise

    def get_by_symbol(self, symbol: str) -> Optional[DomainOptions]:
        """
        Retrieve an option by its symbol.
        
        :param symbol: Option symbol
        :return: Domain option entity or None if not found
        """
        try:
            orm_option = self.session.query(ORMOptions).filter(
                ORMOptions.symbol == symbol
            ).first()
            
            if orm_option:
                return self.mapper.to_domain(orm_option)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving option by symbol {symbol}: {e}")
            raise