from typing import Any, Dict
from sqlalchemy.orm import Session

from infrastructure.repositories.mappers.finance.financial_assets.future_mapper import FutureMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import (
    FinancialAssetBaseRepository
)

from src.infrastructure.models.finance.financial_assets.future import Future as Future_Model
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future as Future_Entity


class FutureRepository(FinancialAssetBaseRepository):
    """Repository for Future derivative instruments."""

    def __init__(self, session: Session):
        """Initialize FutureRepository with database session."""
        super().__init__(session)

    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Future."""
        return Future_Model

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, infra_future: Future_Model) -> Future_Entity:
        """Convert ORM Future to domain Future."""
        if not infra_future:
            return None
        return FutureMapper.to_domain(infra_future)

    def _to_model(self, entity: Future_Entity) -> Future_Model:
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
