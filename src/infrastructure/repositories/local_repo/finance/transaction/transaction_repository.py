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
        Enhanced to handle cascading relationships:
        - Updates holding status (activate/deactivate) based on transaction type
        - Creates/gets account associated with the transaction
        
        Follows the standard _create_or_get pattern from Repository_Local_CreateOrGet_CLAUDE.md
        
        Args:
            transaction_id: Transaction identifier (unique)
            **kwargs: Additional transaction parameters
                - portfolio_id: Portfolio ID (optional)
                - holding_id: Holding ID (optional) 
                - order_id: Order ID (optional)
                - date: Transaction date (default: now)
                - transaction_type: TransactionType enum (default: MARKET_ORDER)
                - account_id: Account identifier (optional)
                - trade_date: Trade date (default: today)
                - value_date: Value date (default: today)
                - settlement_date: Settlement date (default: today)
                - status: TransactionStatus enum (default: PENDING)
                - spread: Transaction spread (default: 0.0)
                - currency_id: Currency ID (default: 1)
                - exchange_id: Exchange ID (default: 1)
                - external_transaction_id: External transaction ID (optional)
                - side: Transaction side (BUY/SELL) for holding updates
                - quantity: Transaction quantity for holding updates
            
        Returns:
            TransactionEntity: Created or existing transaction entity
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If required parameters are invalid
        """
        try:
            # Step 1: Check if entity already exists by unique identifier
            existing_transaction = self.get_by_transaction_id(transaction_id)
            if existing_transaction:
                logger.debug(f"Transaction {transaction_id} already exists, returning existing entity")
                return existing_transaction
            
            # Step 2: Create new entity if not found
            logger.info(f"Creating new transaction: {transaction_id}")
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Import required enums
            from src.domain.entities.finance.transaction.transaction import TransactionType, TransactionStatus
            
            # Create domain entity
            new_transaction = TransactionEntity(
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
            
            # Step 3: Convert to ORM model and persist
            transaction_model = self.mapper.to_orm(new_transaction)
            
            self.session.add(transaction_model)
            self.session.commit()
            
            # Step 4: Convert back to domain entity with database ID
            persisted_entity = self.mapper.to_domain(transaction_model)
            
            # Step 5: Handle cascading relationships after transaction creation
            self._handle_transaction_cascading_relationships(persisted_entity, **kwargs)
            
            logger.info(f"Successfully created transaction {transaction_id} with ID {persisted_entity.id}")
            return persisted_entity
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating/getting transaction {transaction_id}: {str(e)}")
            raise
    
    def _handle_transaction_cascading_relationships(self, transaction: TransactionEntity, **kwargs):
        """
        Handle cascading relationship updates for transactions:
        1. Update holding status (activate/deactivate) based on transaction
        2. Create/get account associated with transaction
        
        Args:
            transaction: The created transaction entity
            **kwargs: Additional parameters for relationship handling
        """
        try:
            # 1. Create/get account for the transaction
            self._create_account_for_transaction(transaction, **kwargs)
            
            # 2. Update holding status based on transaction
            self._update_holding_for_transaction(transaction, **kwargs)
            
        except Exception as e:
            logger.error(f"Error handling cascading relationships for transaction {transaction.id}: {str(e)}")
            # Don't re-raise as this is post-creation enhancement
    
    def _create_account_for_transaction(self, transaction: TransactionEntity, **kwargs):
        """
        Create/get account associated with the transaction.
        
        Args:
            transaction: The transaction entity
            **kwargs: Additional account parameters
        """
        try:
            if transaction.account_id:
                from src.infrastructure.repositories.local_repo.finance.account_repository import AccountRepository
                
                account_repo = AccountRepository(self.session, self.factory)
                
                # Create or get account
                account = account_repo._create_or_get(
                    account_id=transaction.account_id,
                    **{k: v for k, v in kwargs.items() if k.startswith('account_')}
                )
                
                if account:
                    logger.info(f"Ensured account {transaction.account_id} exists for transaction {transaction.id}")
                
        except Exception as e:
            logger.error(f"Error creating account for transaction {transaction.id}: {str(e)}")
    
    def _update_holding_for_transaction(self, transaction: TransactionEntity, **kwargs):
        """
        Update holding status based on the transaction.
        BUY transactions activate holdings, SELL transactions may deactivate them.
        
        Args:
            transaction: The transaction entity
            **kwargs: Additional parameters including side and quantity
        """
        try:
            if transaction.holding_id:
                from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
                from src.infrastructure.models.finance.holding.holding import HoldingModel
                
                # Get holding model to update
                holding_model = self.session.query(HoldingModel).filter(
                    HoldingModel.id == transaction.holding_id
                ).first()
                
                if holding_model:
                    side = kwargs.get('side', 'BUY')  # Default to BUY
                    quantity = kwargs.get('quantity', 0)
                    
                    # Determine if holding should be active based on transaction
                    if side == 'BUY' and quantity > 0:
                        # BUY transaction - activate holding and update quantity
                        holding_model.is_active = True
                        if holding_model.quantity is not None:
                            holding_model.quantity += quantity
                        else:
                            holding_model.quantity = quantity
                        holding_model.end_date = None  # Clear end date for active holding
                        
                        logger.info(f"Activated holding {transaction.holding_id} for BUY transaction {transaction.id}")
                        
                    elif side == 'SELL' and quantity > 0:
                        # SELL transaction - update quantity, deactivate if quantity becomes 0 or negative
                        if holding_model.quantity is not None:
                            holding_model.quantity -= quantity
                            if holding_model.quantity <= 0:
                                holding_model.is_active = False
                                holding_model.end_date = datetime.now().date()
                                logger.info(f"Deactivated holding {transaction.holding_id} for SELL transaction {transaction.id} (quantity <= 0)")
                            else:
                                logger.info(f"Updated holding {transaction.holding_id} quantity for SELL transaction {transaction.id}")
                        else:
                            holding_model.quantity = -quantity  # Set negative quantity for SELL
                    
                    self.session.commit()
                
        except Exception as e:
            logger.error(f"Error updating holding for transaction {transaction.id}: {str(e)}")