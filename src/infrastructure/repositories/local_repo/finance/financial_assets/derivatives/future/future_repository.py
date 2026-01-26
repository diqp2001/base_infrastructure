from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.derivatives.future.future_port import FuturePort
from src.infrastructure.repositories.mappers.finance.financial_assets.future_mapper import FutureMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import (
    FinancialAssetRepository
)

from src.infrastructure.models.finance.financial_assets.derivative.future import FutureModel as Future_Model
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future as Future_Entity


class FutureRepository(FinancialAssetRepository, FuturePort):
    """Repository for Future derivative instruments."""

    def __init__(self, session: Session, factory, mapper: FutureMapper = None):
        """Initialize FutureRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FutureMapper()

    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Future."""
        return Future_Model
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return Future_Entity
    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, infra_future: Future_Model) -> Future_Entity:
        """Convert ORM Future to domain Future."""
        if not infra_future:
            return None
        return self.mapper.to_domain(infra_future)

    def _to_model(self, entity: Future_Entity) -> Future_Model:
        """Convert domain entity to ORM model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
        """Convert domain Future to ORM model."""
        return FutureMapper.to_orm(entity)

    def _to_domain(self, infra_future: Future_Model) -> Future_Entity:
        """Legacy compatibility method."""
        return self._to_entity(infra_future)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_by_id(self, id: int) -> Future_Entity:
        """Fetch a Future by database ID."""
        try:
            future = (
                self.session.query(Future_Model)
                .filter(Future_Model.id == id)
                .first()
            )
            return self._to_domain(future)
        except Exception as e:
            print(f"Error retrieving future by ID {id}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Future_Entity:
        """Fetch a Future by its symbol."""
        try:
            future = (
                self.session.query(Future_Model)
                .filter(Future_Model.symbol == symbol)
                .first()
            )
            return self._to_domain(future)
        except Exception as e:
            print(f"Error retrieving future by symbol {symbol}: {e}")
            return None

    def get_by_symbol_and_expiry(self, symbol: str, expiration_date) -> Future_Entity:
        """Fetch a Future by symbol and expiration date."""
        try:
            future = (
                self.session.query(Future_Model)
                .filter(
                    Future_Model.symbol == symbol,
                    Future_Model.expiration_date == expiration_date,
                )
                .first()
            )
            return self._to_domain(future)
        except Exception as e:
            print(
                f"Error retrieving future {symbol} expiring {expiration_date}: {e}"
            )
            return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def add(self, domain_future: Future_Entity) -> Future_Entity:
        """Add a new Future record to the database."""
        try:
            new_future = FutureMapper.to_orm(domain_future)
            self.session.add(new_future)
            self.session.commit()
            self.session.refresh(new_future)
            return self._to_domain(new_future)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding future: {e}")
            return None

    def _get_next_available_future_id(self) -> int:
        """
        Get the next available ID for future creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(Future_Model.id).order_by(Future_Model.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available future ID: {str(e)}")
            return 1  # Default to 1 if query fails

    def _create_or_get(self, symbol: str, contract_name: str = None,
                       future_type: str = 'INDEX', underlying_asset: str = None,
                       exchange: str = 'CME', currency: str = 'USD',
                       **kwargs) -> Future_Entity:
        """
        Create future entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as CompanyShareRepository._create_or_get().
        
        Args:
            symbol: Future symbol (unique identifier, e.g., 'ESZ5')
            contract_name: Future contract name (defaults to '{symbol} Future')
            future_type: Type of future (INDEX, COMMODITY, BOND, CURRENCY)
            underlying_asset: Underlying asset symbol (e.g., 'SPX' for ES futures)
            exchange: Exchange name (defaults to 'CME')
            currency: Contract currency (defaults to 'USD')
            **kwargs: Additional future parameters
            
        Returns:
            Future_Entity: Created or existing future entity
        """
        # Check if entity already exists by symbol (unique identifier)
        existing_future = self.get_by_symbol(symbol)
        if existing_future:
            return existing_future
        
        try:
            # Generate next available ID
            next_id = self._get_next_available_future_id()
            
            # Create new future entity
            new_future = Future_Entity(
                id=next_id,
                symbol=symbol,
                contract_name=contract_name or f"{symbol} Future",
                future_type=future_type,
                underlying_asset=underlying_asset or symbol,
                exchange=exchange,
                currency=currency,
                is_tradeable=kwargs.get('is_tradeable', True),
                is_active=kwargs.get('is_active', True)
            )
            
            # Add to database
            return self.add(new_future)
            
        except Exception as e:
            print(f"Error creating future for {symbol}: {str(e)}")
            return None
        
    def _get_info_from_market_data_ibkr(self, symbol: str, exchange: str, currency: str) -> Dict[str, Any]:
        """
        Get Future information from MarketData service.
        
        Args:
            symbol: Future symbol
            exchange: Exchange
            currency: Currency
            
        Returns:
            Dict with Future information from MarketData
        """
        try:
            # Attempt to get historical data to verify existence
            if hasattr(self.market_data, 'get_index_historical_data'):
                data = self.market_data.get_future_historical_data(
                    symbol=symbol,
                    exchange=exchange,
                    currency=currency,
                    duration_str="1 D",
                    bar_size_setting="1 day"
                )
                
                if data and len(data) > 0:
                    return {
                        'name': f"{symbol} Future",
                        'base_value': 100.0,  # Default base value
                        'base_date': None,
                        'provider': exchange
                    }
            
            # Return default information if MarketData fails
            return {
                'name': f"{symbol} Future",
                'base_value': 100.0,
                'base_date': None,
                'provider': exchange
            }, self.create(**data)
            
        except Exception as e:
            print(f"Warning: Could not get index info from MarketData for {symbol}: {str(e)}")
            return {
                'name': f"{symbol} Future",
                'base_value': 100.0,
                'base_date': None,
                'provider': exchange
            }
    
    def get_or_create(self, symbol: str, contract_name: str = None, future_type: str = 'INDEX',
                      underlying_asset: str = None, exchange: str = 'CME', currency: str = 'USD', **kwargs) -> Optional[Future_Entity]:
        """
        Get or create a future by symbol with dependency resolution.
        
        Args:
            symbol: Future symbol (e.g., 'ESZ5', 'CLZ5')
            contract_name: Future contract name (optional, will default if not provided)
            future_type: Type of future (INDEX, COMMODITY, BOND, CURRENCY)
            underlying_asset: Underlying asset symbol (e.g., 'SPX' for ES futures)
            exchange: Exchange name (defaults to 'CME')
            currency: Contract currency (defaults to 'USD')
            **kwargs: Additional future parameters
            
        Returns:
            Future entity or None if creation failed
        """
        try:
            # First try to get existing future
            existing = self.get_by_symbol(symbol)
            if existing:
                return existing
            
            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency_entity = currency_local_repo.get_or_create(iso_code=currency)
            
            return self._create_or_get(symbol, contract_name, future_type, underlying_asset, exchange, currency, **kwargs)
            
        except Exception as e:
            print(f"Error in get_or_create for future {symbol}: {e}")
            return None
