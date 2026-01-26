import logging
from typing import Any, Dict, Optional
from datetime import date
from sqlalchemy.orm import Session
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import (
    FinancialAssetRepository
)

logger = logging.getLogger(__name__)

from src.infrastructure.models.finance.financial_assets.index import IndexModel as Index_Model
from src.domain.entities.finance.financial_assets.index.index import Index as Index_Entity
from src.infrastructure.repositories.mappers.finance.financial_assets.index_mapper import IndexMapper
from src.domain.ports.finance.financial_assets.index.index_port import IndexPort


class IndexRepository(FinancialAssetRepository, IndexPort):
    """Repository for Index financial assets."""
    
    def __init__(self, session: Session, factory):
        """Initialize IndexRepository with database session."""
        super().__init__(session)
        self.factory = factory

    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Index."""
        return Index_Model
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return Index_Entity
    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, infra_index: Index_Model) -> Index_Entity:
        """Convert ORM Index model to domain Index entity."""
        if not infra_index:
            return None
        return IndexMapper.to_domain(infra_index)

    def _to_model(self, entity: Index_Entity) -> Index_Model:
        """Convert domain Index entity to ORM model."""
        return IndexMapper.to_orm(entity)

    def _to_domain(self, infra_index: Index_Model) -> Index_Entity:
        """Legacy compatibility method."""
        return self._to_entity(infra_index)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_by_id(self, id: int) -> Index_Entity:
        """Fetch an Index by database ID."""
        try:
            index = (
                self.session.query(Index_Model)
                .filter(Index_Model.id == id)
                .first()
            )
            return self._to_domain(index)
        except Exception as e:
            print(f"Error retrieving index by ID {id}: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Index_Entity:
        """Fetch an Index by its symbol (e.g. SPX, NDX)."""
        try:
            index = (
                self.session.query(Index_Model)
                .filter(Index_Model.symbol == symbol)
                .first()
            )
            return self._to_domain(index)
        except Exception as e:
            print(f"Error retrieving index by symbol {symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def add(self, domain_index: Index_Entity) -> Index_Entity:
        """Add a new Index record to the database."""
        try:
            new_index = IndexMapper.to_orm(domain_index)
            self.session.add(new_index)
            self.session.commit()
            self.session.refresh(new_index)
            return self._to_domain(new_index)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding index: {e}")
            return None
        
    def _get_next_available_index_id(self) -> int:
        """
        Get the next available ID for index creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(Index_Model.id).order_by(Index_Model.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available index ID: {str(e)}")
            return 1  # Default to 1 if query fails

    def get_or_create(self, symbol: str, name: str = None, ticker: str = None,
                      index_type: str = 'Stock', currency_code: str = 'USD',
                      exchange: str = 'CBOE', **kwargs) -> Optional[Index_Entity]:
        """
        Get or create an index with dependency resolution.
        
        Args:
            symbol: Index symbol (e.g., 'SPX', 'NDX')
            name: Index name (defaults to '{symbol} Index')
            ticker: Index ticker (optional)
            index_type: Type of index (Stock, Bond, Commodity, etc.)
            currency_code: Currency ISO code (default: USD)
            exchange: Exchange name (defaults to 'CBOE')
            **kwargs: Additional index parameters
            
        Returns:
            Index entity or None if creation failed
        """
        return self._create_or_get(symbol, name, index_type, currency_code, exchange, **kwargs)

    def _create_or_get(self, symbol: str, name: str = None, 
                       index_type: str = 'Stock', currency: str = 'USD',
                       exchange: str = 'CBOE', **kwargs) -> Index_Entity:
        """
        Create index entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as CompanyShareRepository._create_or_get().
        
        Args:
            symbol: Index symbol (unique identifier, e.g., 'SPX')
            name: Index name (defaults to '{symbol} Index')
            index_type: Type of index (Stock, Bond, Commodity, etc.)
            currency: Index currency (defaults to 'USD')
            exchange: Exchange name (defaults to 'CBOE')
            **kwargs: Additional index parameters
            
        Returns:
            Index_Entity: Created or existing index entity
        """
        # Check if entity already exists by symbol (unique identifier)
        existing_index = self.get_by_symbol(symbol)
        if existing_index:
            return existing_index
        
        try:
            # Generate next available ID
            next_id = self._get_next_available_index_id()
            currency_local_repo = self.factory.currency_local_repo
            currency_object = currency_local_repo.get_or_create(currency)
            # Create new index entity
            new_index = Index_Entity(
                id=next_id,
                symbol=symbol,
                currency_id = currency_object.id,
                name=name or f"{symbol}_Index",
                start_date = date.today()
            )
            
            # Add to database
            return self.add(new_index)
            
        except Exception as e:
            print(f"Error creating index for {symbol}: {str(e)}")
            return None

    def _get_info_from_market_data_ibkr(self, symbol: str, exchange: str, currency: str) -> Dict[str, Any]:
        """
        Get index information from MarketData service.
        
        Args:
            symbol: Index symbol
            exchange: Exchange
            currency: Currency
            
        Returns:
            Dict with index information from MarketData
        """
        try:
            # Attempt to get historical data to verify existence
            if hasattr(self.market_data, 'get_index_historical_data'):
                data = self.market_data.get_index_historical_data(
                    symbol=symbol,
                    exchange=exchange,
                    currency=currency,
                    duration_str="1 D",
                    bar_size_setting="1 day"
                )
                
                if data and len(data) > 0:
                    return {
                        'name': f"{symbol} Index",
                        'base_value': 100.0,  # Default base value
                        'base_date': None,
                        'provider': exchange
                    }
            
            # Return default information if MarketData fails
            return {
                'name': f"{symbol} Index",
                'base_value': 100.0,
                'base_date': None,
                'provider': exchange
            }
            
        except Exception as e:
            print(f"Warning: Could not get index info from MarketData for {symbol}: {str(e)}")
            return {
                'name': f"{symbol} Index",
                'base_value': 100.0,
                'base_date': None,
                'provider': exchange
            }
