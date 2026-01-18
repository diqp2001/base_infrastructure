"""
Currency Repository for local database operations.
Follows the same patterns as other repositories in the project.
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.domain.ports.finance.financial_assets.currency_port import CurrencyPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency
from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel as ORMCurrency, CurrencyRate as ORMCurrencyRate
from src.infrastructure.repositories.mappers.finance.financial_assets.currency_mapper import CurrencyMapper

logger = logging.getLogger(__name__)


class CurrencyRepository(FinancialAssetRepository,CurrencyPort):
    def __init__(self, session: Session):
        """Initialize the repository with a database session."""
        super().__init__(session)
        self.mapper = CurrencyMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Currency."""
        return ORMCurrency
    
    @property
    def entity_class(self):
        """Return the domain entity class for Currency."""
        return DomainCurrency
    
    def add(self, currency: DomainCurrency) -> DomainCurrency:
        """
        Add a single currency to the database.
        
        :param currency: Domain currency entity to add
        :return: The saved currency entity with assigned ID
        :raises: IntegrityError if currency already exists
        """
        try:
            # Convert domain entity to ORM model
            orm_currency = self.mapper.to_orm(currency)
            
            # Add to session and flush to get the ID
            self.session.add(orm_currency)
            self.session.flush()
            
            # Create historical rates if any
            if currency.historical_rates:
                historical_orm_rates = self.mapper.create_historical_rates_orm(currency, orm_currency.id)
                self.session.add_all(historical_orm_rates)
            
            self.session.commit()
            
            logger.info(f"Added currency: {currency.iso_code} ({currency.name}) with ID {orm_currency.id}")
            
            # Update domain entity with assigned ID and return
            currency.asset_id = orm_currency.id
            return currency
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Currency {currency.iso_code} already exists: {e}")
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding currency {currency.iso_code}: {e}")
            raise

    def add_bulk(self, currencies: List[DomainCurrency]) -> List[DomainCurrency]:
        """
        Add multiple currencies in a single transaction.
        
        :param currencies: List of domain currency entities
        :return: List of saved currency entities with assigned IDs
        """
        if not currencies:
            logger.warning("No currencies provided for bulk add")
            return []
        
        try:
            created_currencies = []
            
            for currency in currencies:
                # Convert to ORM model
                orm_currency = self.mapper.to_orm(currency)
                self.session.add(orm_currency)
                self.session.flush()  # Get ID without committing
                
                # Create historical rates
                if currency.historical_rates:
                    historical_orm_rates = self.mapper.create_historical_rates_orm(currency, orm_currency.id)
                    self.session.add_all(historical_orm_rates)
                
                # Update domain entity with ID
                currency.asset_id = orm_currency.id
                created_currencies.append(currency)
            
            self.session.commit()
            logger.info(f"Bulk added {len(created_currencies)} currencies")
            
            return created_currencies
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in bulk currency add: {e}")
            raise

    def get_by_id(self, currency_id: int) -> Optional[DomainCurrency]:
        """
        Retrieve a currency by its ID.
        
        :param currency_id: Database ID of the currency
        :return: Domain currency entity or None if not found
        """
        try:
            orm_currency = self.session.query(ORMCurrency).filter(
                ORMCurrency.id == currency_id
            ).first()
            
            if orm_currency:
                return self.mapper.to_domain(orm_currency)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving currency by ID {currency_id}: {e}")
            raise

    def get_by_iso_code(self, iso_code: str) -> Optional[DomainCurrency]:
        """
        Retrieve a currency by its ISO code.
        
        :param iso_code: ISO 4217 code (e.g., 'USD', 'EUR')
        :return: Domain currency entity or None if not found
        """
        try:
            orm_currency = self.session.query(ORMCurrency).filter(
                ORMCurrency.iso_code == iso_code.upper()
            ).first()
            
            if orm_currency:
                return self.mapper.to_domain(orm_currency)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving currency by ISO code {iso_code}: {e}")
            raise

    def get_by_country(self, country_id: int) -> List[DomainCurrency]:
        """
        Retrieve all currencies for a specific country.
        
        :param country_id: Database ID of the country
        :return: List of domain currency entities
        """
        try:
            orm_currencies = self.session.query(ORMCurrency).filter(
                ORMCurrency.country_id == country_id,
                ORMCurrency.is_active == True
            ).all()
            
            return [self.mapper.to_domain(orm_currency) for orm_currency in orm_currencies]
            
        except Exception as e:
            logger.error(f"Error retrieving currencies for country {country_id}: {e}")
            raise

    def get_major_currencies(self) -> List[DomainCurrency]:
        """
        Retrieve all major currencies (USD, EUR, GBP, JPY, etc.).
        
        :return: List of major currency domain entities
        """
        try:
            orm_currencies = self.session.query(ORMCurrency).filter(
                ORMCurrency.is_major_currency == True,
                ORMCurrency.is_active == True
            ).all()
            
            return [self.mapper.to_domain(orm_currency) for orm_currency in orm_currencies]
            
        except Exception as e:
            logger.error(f"Error retrieving major currencies: {e}")
            raise

    def get_tradeable_currencies(self) -> List[DomainCurrency]:
        """
        Retrieve all tradeable currencies.
        
        :return: List of tradeable currency domain entities
        """
        try:
            orm_currencies = self.session.query(ORMCurrency).filter(
                ORMCurrency.is_tradeable == True,
                ORMCurrency.is_active == True
            ).all()
            
            return [self.mapper.to_domain(orm_currency) for orm_currency in orm_currencies]
            
        except Exception as e:
            logger.error(f"Error retrieving tradeable currencies: {e}")
            raise

    def get_all(self) -> List[DomainCurrency]:
        """
        Retrieve all currencies.
        
        :return: List of all currency domain entities
        """
        try:
            orm_currencies = self.session.query(ORMCurrency).all()
            return [self.mapper.to_domain(orm_currency) for orm_currency in orm_currencies]
            
        except Exception as e:
            logger.error(f"Error retrieving all currencies: {e}")
            raise

    def update(self, currency: DomainCurrency) -> DomainCurrency:
        """
        Update an existing currency.
        
        :param currency: Domain currency entity with updated data
        :return: Updated domain currency entity
        """
        try:
            # Find existing ORM entity
            orm_currency = self.session.query(ORMCurrency).filter(
                ORMCurrency.id == currency.asset_id
            ).first()
            
            if not orm_currency:
                raise ValueError(f"Currency with ID {currency.asset_id} not found")
            
            # Update using mapper
            updated_orm_currency = self.mapper.to_orm(currency, orm_currency)
            
            self.session.commit()
            logger.info(f"Updated currency: {currency.iso_code}")
            
            return self.mapper.to_domain(updated_orm_currency)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating currency {currency.iso_code}: {e}")
            raise

    def delete(self, currency_id: int) -> bool:
        """
        Delete a currency by its ID.
        
        :param currency_id: Database ID of the currency
        :return: True if deleted, False if not found
        """
        try:
            rows_deleted = self.session.query(ORMCurrency).filter(
                ORMCurrency.id == currency_id
            ).delete()
            
            self.session.commit()
            
            if rows_deleted > 0:
                logger.info(f"Deleted currency with ID {currency_id}")
                return True
            else:
                logger.warning(f"Currency with ID {currency_id} not found for deletion")
                return False
                
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting currency {currency_id}: {e}")
            raise

    def add_historical_rates(self, currency_id: int, rates_data: List[Dict[str, Any]]) -> int:
        """
        Add historical exchange rates for a currency.
        
        :param currency_id: Database ID of the currency
        :param rates_data: List of rate data dicts with 'date', 'rate', 'target_currency'
        :return: Number of rates added
        """
        try:
            orm_rates = []
            
            for rate_data in rates_data:
                orm_rate = ORMCurrencyRate(
                    currency_id=currency_id,
                    rate=Decimal(str(rate_data['rate'])),
                    timestamp=rate_data['date'],
                    target_currency=rate_data.get('target_currency', 'USD')
                )
                orm_rates.append(orm_rate)
            
            self.session.add_all(orm_rates)
            self.session.commit()
            
            logger.info(f"Added {len(orm_rates)} historical rates for currency {currency_id}")
            return len(orm_rates)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding historical rates for currency {currency_id}: {e}")
            raise

    def get_rate_at_date(self, currency_id: int, date: datetime, target_currency: str = "USD") -> Optional[Decimal]:
        """
        Get the exchange rate for a currency at a specific date.
        
        :param currency_id: Database ID of the currency
        :param date: Date to find rate for
        :param target_currency: Target currency (default USD)
        :return: Exchange rate or None if not found
        """
        try:
            orm_rate = self.session.query(ORMCurrencyRate).filter(
                ORMCurrencyRate.currency_id == currency_id,
                ORMCurrencyRate.target_currency == target_currency,
                ORMCurrencyRate.timestamp <= date
            ).order_by(ORMCurrencyRate.timestamp.desc()).first()
            
            return orm_rate.rate if orm_rate else None
            
        except Exception as e:
            logger.error(f"Error getting rate for currency {currency_id} at {date}: {e}")
            raise

    def count(self) -> int:
        """
        Count total number of currencies.
        
        :return: Number of currencies in database
        """
        try:
            return self.session.query(ORMCurrency).count()
        except Exception as e:
            logger.error(f"Error counting currencies: {e}")
            raise