"""
Order Repository - handles CRUD operations for Order entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.infrastructure.models.finance.order.order import OrderModel
from src.domain.entities.finance.order.order import Order as OrderEntity
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.order.order_mapper import OrderMapper
from src.domain.ports.finance.order.order_port import OrderPort

logger = logging.getLogger(__name__)


class OrderRepository(BaseLocalRepository, OrderPort):
    """Repository for managing Order entities."""
    
    def __init__(self, session: Session, factory, mapper: OrderMapper = None):
        """Initialize OrderRepository with database session and mapper."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or OrderMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Order."""
        return OrderModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Order."""
        return OrderEntity
    
    def _to_entity(self, model: OrderModel) -> OrderEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: OrderEntity) -> OrderModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
    
    def get_all(self) -> List[OrderEntity]:
        """Retrieve all Order records."""
        models = self.session.query(OrderModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, order_id: int) -> Optional[OrderEntity]:
        """Retrieve an Order by its ID."""
        model = self.session.query(OrderModel).filter(
            OrderModel.id == order_id
        ).first()
        return self._to_entity(model)
    
    def get_by_external_order_id(self, external_order_id: str) -> Optional[OrderEntity]:
        """Retrieve an Order by its external order ID."""
        model = self.session.query(OrderModel).filter(
            OrderModel.external_order_id == external_order_id
        ).first()
        return self._to_entity(model)
    
    def get_by_account_id(self, account_id: str) -> List[OrderEntity]:
        """Retrieve Orders by account ID."""
        models = self.session.query(OrderModel).filter(
            OrderModel.account_id == account_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_portfolio_id(self, portfolio_id: int) -> List[OrderEntity]:
        """Retrieve Orders by portfolio ID."""
        models = self.session.query(OrderModel).filter(
            OrderModel.portfolio_id == portfolio_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_active_orders(self) -> List[OrderEntity]:
        """Retrieve all active orders."""
        from src.domain.entities.finance.order.order import OrderStatus
        
        models = self.session.query(OrderModel).filter(
            OrderModel.status.in_([
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED,
                OrderStatus.PARTIALLY_FILLED
            ])
        ).all()
        return [self._to_entity(model) for model in models]
    
    def add(self, entity: OrderEntity) -> Optional[OrderEntity]:
        """Add a new Order entity to the database."""
        try:
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            
            return self._to_entity(model)
        except Exception as e:
            logger.error(f"Error adding order: {e}")
            self.session.rollback()
            return None
    
    def update(self, entity: OrderEntity) -> Optional[OrderEntity]:
        """Update an existing Order record."""
        try:
            model = self.session.query(OrderModel).filter(
                OrderModel.id == entity.id
            ).first()
            
            if not model:
                return None
            
            # Update model with entity data
            updated_model = self.mapper.to_orm(entity, model)
            self.session.commit()
            return self._to_entity(updated_model)
        except Exception as e:
            logger.error(f"Error updating order {entity.id}: {e}")
            self.session.rollback()
            return None
    
    def delete(self, order_id: int) -> bool:
        """Delete an Order record by ID."""
        try:
            model = self.session.query(OrderModel).filter(
                OrderModel.id == order_id
            ).first()
            
            if not model:
                return False
            
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting order {order_id}: {e}")
            self.session.rollback()
            return False
    
    def _create_or_get(self, external_order_id: str = None, **kwargs) -> Optional[OrderEntity]:
        """
        Create order entity if it doesn't exist, otherwise return existing.
        Enhanced to create cascading relationships:
        - If order is executed (FILLED), creates associated transaction
        - Creates inactive holding related to the order
        
        Follows the standard _create_or_get pattern from Repository_Local_CreateOrGet_CLAUDE.md
        
        Args:
            external_order_id: External order identifier (unique, optional)
            **kwargs: Additional order parameters
                - portfolio_id: Portfolio ID (optional)
                - holding_id: Holding ID (optional)
                - order_type: OrderType enum (default: MARKET)
                - side: OrderSide enum (default: BUY)
                - quantity: Order quantity (default: 0.0)
                - created_at: Creation timestamp (default: now)
                - status: OrderStatus enum (default: PENDING)
                - account_id: Account identifier (optional)
                - price: Order price (optional)
                - stop_price: Stop price (optional)
                - filled_quantity: Filled quantity (default: 0.0)
                - average_fill_price: Average fill price (optional)
                - time_in_force: Time in force (optional)
                - symbol: Asset symbol for holding creation (optional)
            
        Returns:
            OrderEntity: Created or existing order entity
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If required parameters are invalid
        """
        try:
            # Step 1: Check if entity already exists by unique identifier
            if external_order_id:
                existing_order = self.get_by_external_order_id(external_order_id)
                if existing_order:
                    logger.debug(f"Order {external_order_id} already exists, returning existing entity")
                    return existing_order
            
            # Step 2: Create new entity if not found
            logger.info(f"Creating new order: {external_order_id or 'auto-generated'}")
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Import required enums
            from src.domain.entities.finance.order.order import OrderType, OrderSide, OrderStatus
            
            # Create domain entity
            new_order = OrderEntity(
                id=next_id,
                portfolio_id=kwargs.get('portfolio_id'),
                holding_id=kwargs.get('holding_id'),
                order_type=kwargs.get('order_type', OrderType.MARKET),
                side=kwargs.get('side', OrderSide.BUY),
                quantity=kwargs.get('quantity', 0.0),
                created_at=kwargs.get('created_at', datetime.now()),
                status=kwargs.get('status', OrderStatus.PENDING),
                account_id=kwargs.get('account_id'),
                price=kwargs.get('price'),
                stop_price=kwargs.get('stop_price'),
                filled_quantity=kwargs.get('filled_quantity', 0.0),
                average_fill_price=kwargs.get('average_fill_price'),
                time_in_force=kwargs.get('time_in_force'),
                external_order_id=external_order_id
            )
            
            # Step 3: Convert to ORM model and persist
            order_model = self.mapper.to_orm(new_order)
            
            self.session.add(order_model)
            self.session.commit()
            
            # Step 4: Convert back to domain entity with database ID
            persisted_entity = self.mapper.to_domain(order_model)
            
            # Step 5: Handle cascading relationships after order creation
            self._handle_order_cascading_relationships(persisted_entity, **kwargs)
            
            logger.info(f"Successfully created order {external_order_id or 'auto-generated'} with ID {persisted_entity.id}")
            return persisted_entity
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating/getting order {external_order_id or 'auto-generated'}: {str(e)}")
            raise
    
    def _handle_order_cascading_relationships(self, order: OrderEntity, **kwargs):
        """
        Handle cascading relationship creation for orders:
        1. If order is executed (FILLED), create associated transaction
        2. Create inactive holding related to the order
        
        Args:
            order: The created order entity
            **kwargs: Additional parameters for relationship creation
        """
        try:
            # 1. Create transaction if order is executed
            if order.status == OrderStatus.FILLED or (order.filled_quantity > 0 and order.filled_quantity >= order.quantity):
                logger.info(f"Order {order.id} is executed, creating associated transaction")
                self._create_transaction_for_order(order, **kwargs)
            
            # 2. Create inactive holding for the order
            self._create_holding_for_order(order, **kwargs)
            
        except Exception as e:
            logger.error(f"Error handling cascading relationships for order {order.id}: {str(e)}")
            # Don't re-raise as this is post-creation enhancement
    
    def _create_transaction_for_order(self, order: OrderEntity, **kwargs):
        """
        Create a transaction for an executed order.
        
        Args:
            order: The executed order entity
            **kwargs: Additional transaction parameters
        """
        try:
            from src.infrastructure.repositories.local_repo.finance.transaction.transaction_repository import TransactionRepository
            
            transaction_repo = TransactionRepository(self.session, self.factory)
            
            # Generate unique transaction ID
            import uuid
            transaction_id = f"TXN_{order.external_order_id or order.id}_{uuid.uuid4().hex[:8]}"
            
            # Create transaction with order details
            transaction_repo._create_or_get(
                transaction_id=transaction_id,
                order_id=order.id,
                portfolio_id=order.portfolio_id,
                holding_id=order.holding_id,
                account_id=order.account_id,
                external_transaction_id=kwargs.get('external_transaction_id'),
                # Map order type to transaction type
                transaction_type=self._map_order_to_transaction_type(order.order_type),
                **{k: v for k, v in kwargs.items() if k.startswith('transaction_')}
            )
            
            logger.info(f"Created transaction {transaction_id} for order {order.id}")
            
        except Exception as e:
            logger.error(f"Error creating transaction for order {order.id}: {str(e)}")
    
    def _create_holding_for_order(self, order: OrderEntity, **kwargs):
        """
        Create an inactive holding related to the order.
        
        Args:
            order: The order entity
            **kwargs: Additional holding parameters
        """
        try:
            from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
            
            holding_repo = HoldingRepository(self.session, self.factory)
            
            # Use existing holding_id or create new holding
            if not order.holding_id:
                # Create holding with inactive status
                holding = holding_repo._create_or_get(
                    container_id=order.portfolio_id or 1,
                    asset_id=kwargs.get('asset_id'),
                    quantity=0,  # Start with 0 quantity (inactive)
                    symbol=kwargs.get('symbol', 'UNKNOWN'),
                    is_active=False,  # Initially inactive
                    **{k: v for k, v in kwargs.items() if k.startswith('holding_')}
                )
                
                if holding:
                    # Update order with the created holding ID
                    self.session.query(self.model_class).filter(
                        self.model_class.id == order.id
                    ).update({'holding_id': holding.id})
                    self.session.commit()
                    
                    logger.info(f"Created inactive holding {holding.id} for order {order.id}")
            
        except Exception as e:
            logger.error(f"Error creating holding for order {order.id}: {str(e)}")
    
    def _map_order_to_transaction_type(self, order_type: 'OrderType') -> 'TransactionType':
        """
        Map order type to transaction type.
        
        Args:
            order_type: Order type enum
            
        Returns:
            TransactionType: Corresponding transaction type
        """
        from src.domain.entities.finance.transaction.transaction import TransactionType
        from src.domain.entities.finance.order.order import OrderType
        
        mapping = {
            OrderType.MARKET: TransactionType.MARKET_ORDER,
            OrderType.LIMIT: TransactionType.LIMIT_ORDER,
            OrderType.STOP: TransactionType.STOP_ORDER,
            OrderType.STOP_LIMIT: TransactionType.STOP_LIMIT_ORDER
        }
        
        return mapping.get(order_type, TransactionType.MARKET_ORDER)