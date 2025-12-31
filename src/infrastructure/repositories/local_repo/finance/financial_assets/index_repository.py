from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import (
    FinancialAssetBaseRepository
)

from src.infrastructure.models.finance.financial_assets.index import Index as Index_Model
from src.domain.entities.finance.financial_assets.index.index import Index as Index_Entity
from src.infrastructure.repositories.mappers.finance.financial_assets.index_mapper import IndexMapper


class IndexRepository(FinancialAssetBaseRepository):
    """Repository for Index financial assets."""
    
    def __init__(self, session: Session):
        """Initialize IndexRepository with database session."""
        super().__init__(session)

    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Index."""
        return Index_Model

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
            }, self.create(**data)
            
        except Exception as e:
            print(f"Warning: Could not get index info from MarketData for {symbol}: {str(e)}")
            return {
                'name': f"{symbol} Index",
                'base_value': 100.0,
                'base_date': None,
                'provider': exchange
            }
