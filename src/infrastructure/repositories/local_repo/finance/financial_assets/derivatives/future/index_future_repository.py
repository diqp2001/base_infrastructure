import os
from typing import Optional
from sqlalchemy.orm import Session


from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.future_repository import (
    FutureRepository
)
from src.domain.entities.finance.financial_assets.derivatives.future.future import (
    Future as Future_Entity
)
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.ports.finance.financial_assets.derivatives.future.index_future_port import IndexFuturePort
from src.infrastructure.repositories.mappers.finance.financial_assets.index_future_mapper import IndexFutureMapper

class IndexFutureRepository(FutureRepository, IndexFuturePort):
    """
    Repository for INDEX Future instruments (e.g., ES, NQ, RTY).
    Specialization of FutureRepository.
    """

    def __init__(self, session: Session, factory):
        """Initialize IndexFutureRepository with database session."""
        super().__init__(session, factory)
        self.mapper = IndexFutureMapper()
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return self.mapper.entity_class
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return self.mapper.model_class
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
    def add(self, domain_index: IndexFuture) -> IndexFuture:
        """Add a new Index record to the database."""
        try:
            new_index = self.mapper.to_orm(domain_index)
            self.session.add(new_index)
            self.session.commit()
            return self.mapper.to_domain(new_index)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding index: {e}_{os.path.abspath(__file__)}")
            return None
    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    
    def get_by_symbol(self, symbol: str):
        """Fetch a Future by its symbol."""
        try:
            index_future = (
                self.session.query(self.model_class)
                .filter(self.model_class.symbol == symbol)
                .first()
            )
            return self.mapper.to_domain(index_future)
        except Exception as e:
            print(f"Error retrieving future by symbol {symbol}: {e}_{os.path.abspath(__file__)}")
            return None
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
            if existing :
                # Convert Future to IndexFuture entity
                return existing
            
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
            print(f"Error in get_or_create for symbol {symbol}: {e}_{os.path.abspath(__file__)}")
            return None

    
    
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
            return self.mapper.entity_class(
                id=future_entity.id,
                name=future_entity.name,
                symbol=future_entity.symbol,
                currency_id=getattr(future_entity, 'currency_id', None),
                exchange_id=getattr(future_entity, 'exchange_id', None),
                underlying_asset_id=getattr(future_entity, 'underlying_asset_id', None),
                start_date=getattr(future_entity, 'start_date', None),
                end_date=getattr(future_entity, 'end_date', None),
                underlying_index=getattr(future_entity, 'underlying_asset', None)
            )
        except Exception as e:
            print(f"Error converting Future to IndexFuture: {e}_{os.path.abspath(__file__)}")
            return None
