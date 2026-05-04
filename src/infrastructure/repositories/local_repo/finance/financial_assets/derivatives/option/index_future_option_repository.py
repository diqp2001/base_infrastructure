"""
IndexFutureOptionRepository for local database operations.
Specialization of OptionsRepository for index future options.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.domain.ports.finance.financial_assets.derivatives.option.index_future_option_port import IndexFutureOptionPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.options_repository import OptionsRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.index_future_option_mapper import IndexFutureOptionMapper

logger = logging.getLogger(__name__)


class IndexFutureOptionRepository(OptionsRepository, IndexFutureOptionPort):
    """
    Repository for Index Future Option instruments.
    Specialization of OptionsRepository.
    """

    def __init__(self, session: Session, factory):
        """Initialize IndexFutureOptionRepository with database session."""
        super().__init__(session, factory)
        self.mapper = IndexFutureOptionMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for IndexFutureOption."""
        return self.mapper.entity_class
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for IndexFutureOption."""
        return self.mapper.model_class

    def get_by_id(self, id: int):
        """Get index future option by ID."""
        return (
            self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )

    # ------------------------------------------------------------------
    # Index Future Option-specific queries
    # ------------------------------------------------------------------

    def get_by_strike_and_index(self, index_symbol: str, strike_price: float) -> Optional[IndexFutureOption]:
        """
        Fetch an Index Future Option by strike price and index symbol.
        
        Args:
            index_symbol: The underlying index symbol
            strike_price: The strike price
            
        Returns:
            IndexFutureOption entity or None if not found
        """
        try:
            option = (
                self.session.query(self.model_class)
                .filter(
                    self.model_class.strike_price == strike_price,
                    self.model_class.index_symbol == index_symbol
                )
                .first()
            )
            return self.mapper.to_domain(option) if option else None
        except Exception as e:
            logger.error(f"Error retrieving index future option by strike {strike_price} and index {index_symbol}: {e}")
            return None

    def add(self, domain_option: IndexFutureOption) -> IndexFutureOption:
        """Add a new Index Future Option record to the database."""
        try:
            new_option = self.mapper.to_orm(domain_option)
            self.session.add(new_option)
            self.session.commit()
            return self.mapper.to_domain(new_option)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding index future option: {e}")
            return None

    def get_by_symbol(self, symbol: str) -> Optional[IndexFutureOption]:
        """Fetch an Index Future Option by its symbol."""
        try:
            option = (
                self.session.query(self.model_class)
                .filter(self.model_class.symbol == symbol)
                .first()
            )
            return self.mapper.to_domain(option) if option else None
        except Exception as e:
            logger.error(f"Error retrieving index future option by symbol {symbol}: {e}")
            return None

    def get_by_index_symbol(self, index_symbol: str) -> list:
        """
        Get index future options by underlying index symbol.
        
        Args:
            index_symbol: The underlying index symbol (e.g., 'SPX', 'NDX', 'RUT')
            
        Returns:
            List of IndexFutureOption entities for the underlying index
        """
        try:
            options = (
                self.session.query(self.model_class)
                .filter(self.model_class.index_symbol == index_symbol)
                .all()
            )
            return [self.mapper.to_domain(option) for option in options]
        except Exception as e:
            logger.error(f"Error retrieving index future options by index symbol {index_symbol}: {e}")
            return []

    def get_by_symbol_and_strike(self, symbol: str, strike_price: float) -> Optional[IndexFutureOption]:
        """Get index future option by symbol and strike price."""
        try:
            option = (
                self.session.query(self.model_class)
                .filter(
                    self.model_class.symbol == symbol,
                    self.model_class.strike_price == strike_price
                )
                .first()
            )
            return self.mapper.to_domain(option) if option else None
        except Exception as e:
            logger.error(f"Error retrieving index future option by symbol {symbol} and strike {strike_price}: {e}")
            return None

    def get_all(self) -> list:
        """Get all index future options."""
        try:
            options = self.session.query(self.model_class).all()
            return [self.mapper.to_domain(option) for option in options]
        except Exception as e:
            logger.error(f"Error retrieving all index future options: {e}")
            return []

    def update(self, entity: IndexFutureOption) -> Optional[IndexFutureOption]:
        """Update index future option entity."""
        try:
            model = self.session.query(self.model_class).filter(self.model_class.id == entity.id).first()
            if model:
                updated_model = self.mapper.to_orm(entity)
                for key, value in updated_model.__dict__.items():
                    if not key.startswith('_'):
                        setattr(model, key, value)
                self.session.commit()
                return self.mapper.to_domain(model)
            return None
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating index future option: {e}")
            return None

    def delete(self, entity_id: int) -> bool:
        """Delete index future option entity."""
        try:
            model = self.session.query(self.model_class).filter(self.model_class.id == entity_id).first()
            if model:
                self.session.delete(model)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting index future option {entity_id}: {e}")
            return False