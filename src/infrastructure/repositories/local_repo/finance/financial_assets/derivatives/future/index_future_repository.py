from typing import Optional
from sqlalchemy.orm import Session


from infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.future_repository import (
    FutureRepository
)
from src.domain.entities.finance.financial_assets.derivatives.future.future import (
    Future as Future_Entity
)
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.ports.finance.financial_assets.derivatives.future.index_future_port import IndexFuturePort

class IndexFutureRepository(FutureRepository, IndexFuturePort):
    """
    Repository for INDEX Future instruments (e.g., ES, NQ, RTY).
    Specialization of FutureRepository.
    """

    def __init__(self, session: Session, factory):
        """Initialize IndexFutureRepository with database session."""
        super().__init__(session, factory)
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return IndexFuture
    # ------------------------------------------------------------------
    # Index-specific queries
    # ------------------------------------------------------------------

    def get_by_index_symbol(self, symbol: str) -> Optional[Future_Entity]:
        """
        Fetch an INDEX future by symbol.
        Ensures future_type = 'INDEX'.
        """
        future = self.get_by_symbol(symbol)

        if future and future.future_type == "INDEX":
            return future

        return None

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    def get_or_create(self, symbol: str) -> Optional[IndexFuture]:
        """
        Get or create an index future by symbol.
        Implementation of IndexFuturePort interface.
        
        Args:
            symbol: The future symbol (e.g., 'ESZ25', 'NQH25')
            
        Returns:
            IndexFuture entity or None if creation/retrieval failed
        """
        try:
            # First try to get existing
            existing = self.get_by_symbol(symbol)
            if existing and existing.future_type == "INDEX":
                # Convert Future to IndexFuture entity
                return self._future_to_index_future(existing)
            
            # Create new index future with minimal parameters
            future_entity = self._create_or_get(
                symbol=symbol,
                contract_name=f"{symbol} Index Future",
                future_type="INDEX",
                underlying_asset="INDEX",  # Default for index futures
                exchange="CME",  # Default exchange
                currency="USD",  # Default currency
            )
            
            return self._future_to_index_future(future_entity) if future_entity else None
        except Exception as e:
            print(f"Error in get_or_create for symbol {symbol}: {e}")
            return None

    def create_or_get_index_future(
        self,
        symbol: str,
        underlying_index: str,
        exchange: str = "CME",
        currency: str = "USD",
        contract_name: Optional[str] = None,
        **kwargs
    ) -> Future_Entity:
        """
        Create or retrieve an INDEX future (legacy method).

        Args:
            symbol: Future symbol (e.g., 'ESZ5')
            underlying_index: Underlying index (e.g., 'SPX')
            exchange: Exchange (default CME)
            currency: Currency (default USD)
            contract_name: Optional explicit contract name
            **kwargs: Additional Future parameters

        Returns:
            Future_Entity
        """
        return self._create_or_get(
            symbol=symbol,
            contract_name=contract_name or f"{symbol} Index Future",
            future_type="INDEX",
            underlying_asset=underlying_index,
            exchange=exchange,
            currency=currency,
            **kwargs,
        )
    
    def _future_to_index_future(self, future_entity: Future_Entity) -> Optional[IndexFuture]:
        """
        Convert Future entity to IndexFuture entity.
        
        Args:
            future_entity: Future entity to convert
            
        Returns:
            IndexFuture entity or None if conversion failed
        """
        try:
            # Create IndexFuture from Future entity attributes
            # Note: This is a simplified conversion. In a real implementation,
            # you might need more sophisticated mapping logic
            return IndexFuture(
                symbol=future_entity.symbol,
                name=future_entity.name,
                exchange=future_entity.exchange,
                currency=future_entity.currency,
                underlying_index=future_entity.underlying_asset,
                contract_size=getattr(future_entity, 'contract_size', 1),
                tick_size=getattr(future_entity, 'tick_size', 0.01),
                expiry_date=getattr(future_entity, 'expiry_date', None),
                market_sector=getattr(future_entity, 'market_sector', 'INDEX'),
                asset_class=getattr(future_entity, 'asset_class', 'DERIVATIVE')
            )
        except Exception as e:
            print(f"Error converting Future to IndexFuture: {e}")
            return None
