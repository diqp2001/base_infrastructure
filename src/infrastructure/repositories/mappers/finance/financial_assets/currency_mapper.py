"""
Mapper for Currency domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with country relationships, historical rates, and factor integration.
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.currency import Currency as DomainCurrency, CurrencyRate as DomainCurrencyRate
from src.infrastructure.models.finance.financial_assets.currency import Currency as ORMCurrency, CurrencyRate as ORMCurrencyRate
from src.infrastructure.models.finance.financial_assets.currency_factors import CurrencyFactor, CurrencyFactorValue
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository


class CurrencyMapper:
    """Mapper for Currency domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCurrency) -> DomainCurrency:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCurrency(
            asset_id=orm_obj.id,
            name=orm_obj.name,
            iso_code=orm_obj.iso_code,
            country_id=orm_obj.country_id
        )
        
        # Set exchange rate data
        if orm_obj.exchange_rate_to_usd:
            domain_entity.current_rate_to_usd = orm_obj.exchange_rate_to_usd
            domain_entity.last_rate_update = orm_obj.last_rate_update
        
        # Set currency properties
        domain_entity.is_major_currency = orm_obj.is_major_currency
        domain_entity.decimal_places = orm_obj.decimal_places
        domain_entity.is_active = orm_obj.is_active
        domain_entity.is_tradeable = orm_obj.is_tradeable
        
        # Load historical rates if available
        if hasattr(orm_obj, 'historical_rates') and orm_obj.historical_rates:
            for orm_rate in orm_obj.historical_rates:
                domain_rate = DomainCurrencyRate(
                    rate=orm_rate.rate,
                    timestamp=orm_rate.timestamp,
                    target_currency=orm_rate.target_currency
                )
                domain_entity.historical_rates.append(domain_rate)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCurrency, orm_obj: Optional[ORMCurrency] = None) -> ORMCurrency:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCurrency()
        
        # Map basic fields
        orm_obj.name = domain_obj.name
        orm_obj.iso_code = domain_obj.iso_code
        orm_obj.country_id = domain_obj.country_id
        
        # Map exchange rate data
        if domain_obj.current_rate_to_usd:
            orm_obj.exchange_rate_to_usd = domain_obj.current_rate_to_usd
            orm_obj.last_rate_update = domain_obj.last_rate_update or datetime.now()
        
        # Map currency properties
        orm_obj.is_major_currency = domain_obj.is_major_currency
        orm_obj.decimal_places = domain_obj.decimal_places
        orm_obj.is_active = domain_obj.is_active
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        return orm_obj

    @staticmethod
    def create_historical_rates_orm(domain_obj: DomainCurrency, currency_id: int) -> List[ORMCurrencyRate]:
        """
        Create ORM models for historical currency rates.
        
        :param domain_obj: Domain currency entity
        :param currency_id: Database ID of the currency
        :return: List of ORM CurrencyRate objects
        """
        orm_rates = []
        
        for domain_rate in domain_obj.historical_rates:
            orm_rate = ORMCurrencyRate(
                currency_id=currency_id,
                rate=domain_rate.rate,
                timestamp=domain_rate.timestamp,
                target_currency=domain_rate.target_currency
            )
            orm_rates.append(orm_rate)
        
        return orm_rates

    @staticmethod
    def populate_factor_data(domain_obj: DomainCurrency, currency_id: int, factor_repository: CurrencyFactorRepository) -> List[CurrencyFactorValue]:
        """
        Populate currency factor values from domain entity historical rates.
        
        :param domain_obj: Domain currency entity with historical rates
        :param currency_id: Database ID of the currency
        :param factor_repository: Repository for managing currency factors
        :return: List of created factor value records
        """
        created_values = []
        
        if not domain_obj.historical_rates:
            return created_values
        
        # Create or get exchange rate factor
        factor_name = f"{domain_obj.iso_code}_exchange_rate_usd"
        
        try:
            factor = factor_repository.get_by_name(factor_name)
        except:
            # Create new factor
            factor = factor_repository.add_factor(
                name=factor_name,
                group="exchange_rate",
                subgroup="historical",
                data_type="numeric",
                source="currency_mapper",
                definition=f"Exchange rate for {domain_obj.name} vs USD"
            )
        
        # Populate factor values from historical rates
        for domain_rate in domain_obj.historical_rates:
            try:
                factor_value = factor_repository.add_factor_value(
                    factor_id=factor.id,
                    entity_id=currency_id,
                    date=domain_rate.timestamp.date() if isinstance(domain_rate.timestamp, datetime) else domain_rate.timestamp,
                    value=domain_rate.rate
                )
                created_values.append(factor_value)
            except Exception as e:
                print(f"Warning: Failed to create factor value for {factor_name} on {domain_rate.timestamp}: {str(e)}")
                continue
        
        return created_values

    @staticmethod
    def populate_current_rate_factor(domain_obj: DomainCurrency, currency_id: int, factor_repository: CurrencyFactorRepository) -> Optional[CurrencyFactorValue]:
        """
        Populate current exchange rate as a factor value.
        
        :param domain_obj: Domain currency entity with current rate
        :param currency_id: Database ID of the currency
        :param factor_repository: Repository for managing currency factors
        :return: Created factor value record or None
        """
        if not domain_obj.current_rate_to_usd:
            return None
        
        # Create or get current rate factor
        factor_name = f"{domain_obj.iso_code}_current_rate_usd"
        
        try:
            factor = factor_repository.get_by_name(factor_name)
        except:
            # Create new factor
            factor = factor_repository.add_factor(
                name=factor_name,
                group="exchange_rate",
                subgroup="current",
                data_type="numeric",
                source="currency_mapper",
                definition=f"Current exchange rate for {domain_obj.name} vs USD"
            )
        
        # Create factor value for current rate
        current_date = domain_obj.last_rate_update.date() if domain_obj.last_rate_update else date.today()
        
        try:
            factor_value = factor_repository.add_factor_value(
                factor_id=factor.id,
                entity_id=currency_id,
                date=current_date,
                value=domain_obj.current_rate_to_usd
            )
            return factor_value
        except Exception as e:
            print(f"Warning: Failed to create current rate factor value for {factor_name}: {str(e)}")
            return None

    @staticmethod
    def load_factor_data(orm_obj: ORMCurrency, factor_repository: CurrencyFactorRepository) -> DomainCurrency:
        """
        Load currency domain entity with factor data populated as historical rates.
        
        :param orm_obj: ORM Currency model
        :param factor_repository: Repository for accessing currency factors
        :return: Domain currency entity with factor data as historical rates
        """
        # Convert ORM to domain first
        domain_entity = CurrencyMapper.to_domain(orm_obj)
        
        # Load factor values as historical rates
        try:
            # Get exchange rate factor
            factor_name = f"{domain_entity.iso_code}_exchange_rate_usd"
            factor = factor_repository.get_by_name(factor_name)
            
            if factor:
                # Get all factor values for this currency
                factor_values = factor_repository.get_factor_values_by_entity(orm_obj.id)
                
                # Convert factor values to domain currency rates
                for fv in factor_values:
                    if fv.factor_id == factor.id:
                        domain_rate = DomainCurrencyRate(
                            rate=fv.value,
                            timestamp=datetime.combine(fv.date, datetime.min.time()),
                            target_currency="USD"
                        )
                        domain_entity.historical_rates.append(domain_rate)
                
                # Sort by date
                domain_entity.historical_rates.sort(key=lambda r: r.timestamp)
                
        except Exception as e:
            print(f"Warning: Failed to load factor data for currency {domain_entity.name}: {str(e)}")
        
        return domain_entity