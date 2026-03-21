"""
Transaction Repository - handles CRUD operations for Transaction entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

import logging
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session

from src.infrastructure.models.finance.transaction.transaction import TransactionModel
from src.domain.entities.finance.transaction.transaction import Transaction as TransactionEntity
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.transaction.transaction_mapper import TransactionMapper
from src.domain.ports.finance.transaction.transaction_port import TransactionPort

logger = logging.getLogger(__name__)


class TransactionRepository(BaseLocalRepository, TransactionPort):
    """Repository for managing Transaction entities."""
    
    def __init__(self, session: Session, factory, mapper: TransactionMapper = None):
        """Initialize TransactionRepository with database session and mapper."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or TransactionMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Transaction."""
        return TransactionModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Transaction."""
        return TransactionEntity
    
    def _to_entity(self, model: TransactionModel) -> TransactionEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: TransactionEntity) -> TransactionModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
    
    def get_all(self) -> List[TransactionEntity]:
        """Retrieve all Transaction records."""
        models = self.session.query(TransactionModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, transaction_id: int) -> Optional[TransactionEntity]:
        """Retrieve a Transaction by its ID."""
        model = self.session.query(TransactionModel).filter(
            TransactionModel.id == transaction_id
        ).first()
        return self._to_entity(model)
    
    def get_by_transaction_id(self, transaction_id: str) -> Optional[TransactionEntity]:
        """Retrieve a Transaction by its transaction ID."""
        model = self.session.query(TransactionModel).filter(
            TransactionModel.transaction_id == transaction_id
        ).first()
        return self._to_entity(model)
    
    def get_by_external_transaction_id(self, external_transaction_id: str) -> Optional[TransactionEntity]:
        """Retrieve a Transaction by its external transaction ID."""
        model = self.session.query(TransactionModel).filter(
            TransactionModel.external_transaction_id == external_transaction_id
        ).first()
        return self._to_entity(model)
    
    def get_by_account_id(self, account_id: str) -> List[TransactionEntity]:
        """Retrieve Transactions by account ID."""
        models = self.session.query(TransactionModel).filter(
            TransactionModel.account_id == account_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_portfolio_id(self, portfolio_id: int) -> List[TransactionEntity]:
        """Retrieve Transactions by portfolio ID."""
        models = self.session.query(TransactionModel).filter(
            TransactionModel.portfolio_id == portfolio_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_order_id(self, order_id: int) -> List[TransactionEntity]:
        """Retrieve Transactions by order ID."""
        models = self.session.query(TransactionModel).filter(
            TransactionModel.order_id == order_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def add(self, entity: TransactionEntity) -> Optional[TransactionEntity]:
        """Add a new Transaction entity to the database."""
        try:
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            
            return self._to_entity(model)
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            self.session.rollback()
            return None
    
    def update(self, entity: TransactionEntity) -> Optional[TransactionEntity]:
        """Update an existing Transaction record."""
        try:
            model = self.session.query(TransactionModel).filter(
                TransactionModel.id == entity.id
            ).first()
            
            if not model:
                return None
            
            # Update model with entity data
            updated_model = self.mapper.to_orm(entity, model)
            self.session.commit()
            return self._to_entity(updated_model)
        except Exception as e:
            logger.error(f"Error updating transaction {entity.id}: {e}")
            self.session.rollback()
            return None
    
    def delete(self, transaction_id: int) -> bool:
        """Delete a Transaction record by ID."""
        try:
            model = self.session.query(TransactionModel).filter(
                TransactionModel.id == transaction_id
            ).first()
            
            if not model:
                return False
            
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting transaction {transaction_id}: {e}")
            self.session.rollback()
            return False
    
    def _create_or_get(self, transaction_id: str, **kwargs) -> Optional[TransactionEntity]:
        """
        Create transaction entity if it doesn't exist, otherwise return existing.
        
        Args:
            transaction_id: Transaction identifier (unique)
            **kwargs: Additional transaction parameters
            
        Returns:
            TransactionEntity: Created or existing transaction
        """
        try:
            # Check if entity already exists by transaction_id
            existing = self.get_by_transaction_id(transaction_id)
            if existing:
                return existing
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Create new transaction entity
            from src.domain.entities.finance.transaction.transaction import TransactionType, TransactionStatus
            
            transaction = TransactionEntity(
                id=next_id,
                portfolio_id=kwargs.get('portfolio_id'),
                holding_id=kwargs.get('holding_id'),
                order_id=kwargs.get('order_id'),
                date=kwargs.get('date', datetime.now()),
                transaction_type=kwargs.get('transaction_type', TransactionType.MARKET_ORDER),
                transaction_id=transaction_id,
                account_id=kwargs.get('account_id'),
                trade_date=kwargs.get('trade_date', date.today()),
                value_date=kwargs.get('value_date', date.today()),
                settlement_date=kwargs.get('settlement_date', date.today()),
                status=kwargs.get('status', TransactionStatus.PENDING),
                spread=kwargs.get('spread', 0.0),
                currency_id=kwargs.get('currency_id', 1),  # Default to USD
                exchange_id=kwargs.get('exchange_id', 1),  # Default exchange
                external_transaction_id=kwargs.get('external_transaction_id')
            )
            
            # Add to database
            return self.add(transaction)
            
        except Exception as e:
            logger.error(f"Error creating transaction {transaction_id}: {e}")
            return None