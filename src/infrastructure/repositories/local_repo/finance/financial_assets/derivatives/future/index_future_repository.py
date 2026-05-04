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
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.future.index_future_mapper import IndexFutureMapper

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
    def get_by_id(self, id: int):
        return (
            self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )
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
    def get_by_id(self, id: int):
        return (
            self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )
    
    
    
    
