"""
CompanyShareOption Repository for local database operations.
Follows the same patterns as other repositories in the project.
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption as DomainCompanyShareOption
from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import CompanyShareOptionModel as ORMCompanyShareOption
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.company_share_option_mapper import CompanyShareOptionMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.options_repository import OptionsRepository

logger = logging.getLogger(__name__)


class CompanyShareOptionRepository(OptionsRepository):
    """Repository for company share option operations in the local database."""

    def __init__(self, session: Session, factory):
        """Initialize CompanyShareOptionRepository with database session."""
        super().__init__(session, factory)
        self.mapper = CompanyShareOptionMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for CompanyShareOptions."""
        return ORMCompanyShareOption
    
    @property
    def entity_class(self):
        """Return the domain entity class for CompanyShareOptions."""
        return DomainCompanyShareOption

    def get_or_create(self, ticker: str = None, name: str = None, symbol: str = None, 
                      currency_code: str = "USD", option_type: str = None, 
                      underlying_asset_id: int = None) -> Optional[DomainCompanyShareOption]:
        """
        Get or create a company share option with dependency resolution.
        
        Args:
            ticker: Option ticker (optional)
            name: Option name (optional)
            symbol: Option symbol (optional) 
            currency_code: Currency ISO code (default: USD)
            option_type: Type of option (CALL/PUT)
            underlying_asset_id: Required ID of the underlying company share
            
        Returns:
            Domain company share option entity or None if creation failed
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
            
            # Validate underlying asset exists and is a company share if provided
            if underlying_asset_id:
                from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
                # Query to check if underlying company share exists
                underlying_exists = self.session.query(CompanyShareModel).filter(
                    CompanyShareModel.id == underlying_asset_id
                ).first()
                
                if not underlying_exists:
                    logger.error(f"Underlying company share with ID {underlying_asset_id} does not exist")
                    return None
            
            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency = currency_local_repo.get_or_create(iso_code=currency_code)
            
            # Create new company share option
            new_option = DomainCompanyShareOption(
                id=None,
                name=name or f"Company Share Option {ticker or symbol}",
                symbol=symbol or ticker,
                currency_id=currency.asset_id if currency else None,
                underlying_asset_id=underlying_asset_id,
                option_type=option_type or "call"
            )
            
            return self.add(new_option)
            
        except Exception as e:
            logger.error(f"Error in get_or_create for company share option {ticker or symbol}: {e}")
            return None
    def add(self, option):
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
            
            
            
            return self.mapper.to_domain(orm_option)
            
        except IntegrityError as e:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding option {option}: {e}")
            raise
    def get_by_company_share_id(self, company_share_id: int) -> List[DomainCompanyShareOption]:
        """
        Retrieve company share options by their underlying company share ID.
        
        Args:
            company_share_id: ID of the underlying company share
            
        Returns:
            List of domain company share option entities
        """
        try:
            orm_options = self.session.query(ORMCompanyShareOption).filter(
                ORMCompanyShareOption.underlying_asset_id == company_share_id
            ).all()
            
            return [self.mapper.to_domain(orm_option) for orm_option in orm_options]
            
        except Exception as e:
            logger.error(f"Error retrieving company share options by company share ID {company_share_id}: {e}")
            raise

    def get_by_option_type(self, option_type: str) -> List[DomainCompanyShareOption]:
        """
        Retrieve company share options by their option type.
        
        Args:
            option_type: Type of option (call/put)
            
        Returns:
            List of domain company share option entities
        """
        try:
            orm_options = self.session.query(ORMCompanyShareOption).filter(
                ORMCompanyShareOption.option_type == option_type.lower()
            ).all()
            
            return [self.mapper.to_domain(orm_option) for orm_option in orm_options]
            
        except Exception as e:
            logger.error(f"Error retrieving company share options by option type {option_type}: {e}")
            raise

    def get_active_options(self) -> List[DomainCompanyShareOption]:
        """
        Retrieve all active company share options (end_date is None or in the future).
        
        Returns:
            List of active domain company share option entities
        """
        try:
            from datetime import date
            current_date = date.today()
            
            orm_options = self.session.query(ORMCompanyShareOption).filter(
                (ORMCompanyShareOption.end_date.is_(None)) | 
                (ORMCompanyShareOption.end_date > current_date)
            ).all()
            
            return [self.mapper.to_domain(orm_option) for orm_option in orm_options]
            
        except Exception as e:
            logger.error(f"Error retrieving active company share options: {e}")
            raise