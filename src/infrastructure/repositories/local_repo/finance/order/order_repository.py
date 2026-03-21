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
    
    def _create_or_get(self, **kwargs) -> Optional[OrderEntity]:
        """
        Create order entity if it doesn't exist, otherwise return existing.
        
        Args:
            **kwargs: Order parameters
            
        Returns:
            OrderEntity: Created or existing order
        """
        try:
            # Check if entity already exists by external_order_id if provided
            external_order_id = kwargs.get('external_order_id')
            if external_order_id:
                existing = self.get_by_external_order_id(external_order_id)
                if existing:
                    return existing
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Create new order entity
            from src.domain.entities.finance.order.order import OrderType, OrderSide, OrderStatus
            
            order = OrderEntity(
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
            
            # Add to database
            return self.add(order)
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None