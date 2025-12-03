"""
Position Repository - handles CRUD operations for Position entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.position import Position as PositionModel
from src.domain.entities.finance.position import Position as PositionEntity
from src.infrastructure.repositories.base_repository import BaseRepository


class PositionRepository(BaseRepository):
    """Repository for managing Position entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Position."""
        return PositionModel
    
    def _to_entity(self, model: PositionModel) -> PositionEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return PositionEntity(
            id=model.id,
            portfolio_id=model.portfolio_id,
            asset_id=model.asset_id,
            asset_type=model.asset_type,
            symbol=model.symbol,
            quantity=Decimal(str(model.quantity)) if model.quantity else Decimal('0'),
            average_cost=Decimal(str(model.average_cost)) if model.average_cost else Decimal('0'),
            current_price=Decimal(str(model.current_price)) if model.current_price else Decimal('0')
        )
    
    def _to_model(self, entity: PositionEntity) -> PositionModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PositionModel(
            portfolio_id=entity.portfolio_id,
            asset_id=entity.asset_id,
            asset_type=entity.asset_type,
            symbol=entity.symbol,
            quantity=float(entity.quantity),
            average_cost=float(entity.average_cost),
            current_price=float(entity.current_price),
            cost_basis=float(entity.quantity * entity.average_cost),
            market_value=float(entity.quantity * entity.current_price),
            unrealized_pnl=float((entity.current_price - entity.average_cost) * entity.quantity),
            position_type='LONG',
            currency='USD',
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def get_all(self) -> List[PositionEntity]:
        """Retrieve all Position records."""
        models = self.session.query(PositionModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, position_id: int) -> Optional[PositionEntity]:
        """Retrieve Position by its ID."""
        model = self.session.query(PositionModel).filter(
            PositionModel.id == position_id
        ).first()
        return self._to_entity(model)
    
    def get_by_portfolio_id(self, portfolio_id: int) -> List[PositionEntity]:
        """Retrieve all positions for a specific portfolio."""
        models = self.session.query(PositionModel).filter(
            PositionModel.portfolio_id == portfolio_id,
            PositionModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_symbol(self, symbol: str) -> List[PositionEntity]:
        """Retrieve all positions for a specific symbol."""
        models = self.session.query(PositionModel).filter(
            PositionModel.symbol == symbol.upper(),
            PositionModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_portfolio_and_symbol(self, portfolio_id: int, symbol: str) -> Optional[PositionEntity]:
        """Retrieve position for a specific portfolio and symbol."""
        model = self.session.query(PositionModel).filter(
            PositionModel.portfolio_id == portfolio_id,
            PositionModel.symbol == symbol.upper(),
            PositionModel.is_active == True
        ).first()
        return self._to_entity(model)
    
    def get_active_positions(self) -> List[PositionEntity]:
        """Retrieve all active positions."""
        models = self.session.query(PositionModel).filter(
            PositionModel.is_active == True,
            PositionModel.is_closed == False,
            PositionModel.quantity > 0
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_asset_type(self, asset_type: str) -> List[PositionEntity]:
        """Retrieve positions by asset type."""
        models = self.session.query(PositionModel).filter(
            PositionModel.asset_type == asset_type,
            PositionModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_position(self, portfolio_id: int, symbol: str) -> bool:
        """Check if a position exists for a portfolio and symbol."""
        return self.session.query(PositionModel).filter(
            PositionModel.portfolio_id == portfolio_id,
            PositionModel.symbol == symbol.upper(),
            PositionModel.is_active == True
        ).first() is not None
    
    def add(self, entity: PositionEntity) -> PositionEntity:
        """Add a new Position entity to the database."""
        # Check for existing position
        if self.exists_position(entity.portfolio_id, entity.symbol):
            existing = self.get_by_portfolio_and_symbol(entity.portfolio_id, entity.symbol)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, position_id: int, **kwargs) -> Optional[PositionEntity]:
        """Update an existing Position record."""
        model = self.session.query(PositionModel).filter(
            PositionModel.id == position_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        # Recalculate derived fields
        if model.quantity and model.average_cost:
            model.cost_basis = float(model.quantity * model.average_cost)
        
        if model.quantity and model.current_price:
            model.market_value = float(model.quantity * model.current_price)
            model.unrealized_pnl = float((model.current_price - model.average_cost) * model.quantity)
            model.unrealized_pnl_percent = (
                (model.current_price - model.average_cost) / model.average_cost * 100
                if model.average_cost > 0 else 0
            )
        
        model.updated_at = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def update_price(self, position_id: int, new_price: float) -> Optional[PositionEntity]:
        """Update position with new market price."""
        return self.update(position_id, current_price=new_price, last_valuation_date=datetime.now())
    
    def update_quantity(self, position_id: int, new_quantity: float, 
                       new_average_cost: float = None) -> Optional[PositionEntity]:
        """Update position quantity and optionally average cost."""
        update_data = {'quantity': new_quantity}
        if new_average_cost is not None:
            update_data['average_cost'] = new_average_cost
        
        return self.update(position_id, **update_data)
    
    def close_position(self, position_id: int) -> Optional[PositionEntity]:
        """Close a position."""
        return self.update(
            position_id, 
            is_closed=True, 
            is_active=False,
            position_closed_at=datetime.now(),
            quantity=0
        )
    
    def delete(self, position_id: int) -> bool:
        """Delete a Position record by ID."""
        model = self.session.query(PositionModel).filter(
            PositionModel.id == position_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def _get_next_available_position_id(self) -> int:
        """
        Get the next available ID for position creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(PositionModel.id).order_by(PositionModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available position ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get_position(self, portfolio_id: int, symbol: str, asset_type: str = "EQUITY",
                               quantity: float = 0, average_cost: float = 0,
                               asset_id: int = None) -> PositionEntity:
        """
        Create position entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as other repositories' _create_or_get_* methods.
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Asset symbol
            asset_type: Type of asset
            quantity: Position quantity
            average_cost: Average cost per unit
            asset_id: Asset ID reference
            
        Returns:
            PositionEntity: Created or existing position
        """
        # Check if entity already exists
        if self.exists_position(portfolio_id, symbol):
            return self.get_by_portfolio_and_symbol(portfolio_id, symbol)
        
        try:
            # Get next available ID
            next_id = self._get_next_available_position_id()
            
            # Create new position entity
            position = PositionEntity(
                id=next_id,
                portfolio_id=portfolio_id,
                asset_id=asset_id or next_id,
                asset_type=asset_type,
                symbol=symbol.upper(),
                quantity=Decimal(str(quantity)),
                average_cost=Decimal(str(average_cost)),
                current_price=Decimal(str(average_cost))  # Start with cost as price
            )
            
            # Add to database
            return self.add(position)
            
        except Exception as e:
            print(f"Error creating position {symbol} for portfolio {portfolio_id}: {str(e)}")
            return None
    
    def get_portfolio_value(self, portfolio_id: int) -> Decimal:
        """Get total market value of all positions in a portfolio."""
        total = self.session.query(PositionModel.market_value).filter(
            PositionModel.portfolio_id == portfolio_id,
            PositionModel.is_active == True
        ).all()
        
        return sum(Decimal(str(value[0])) for value in total if value[0])
    
    def get_portfolio_unrealized_pnl(self, portfolio_id: int) -> Decimal:
        """Get total unrealized P&L for a portfolio."""
        total = self.session.query(PositionModel.unrealized_pnl).filter(
            PositionModel.portfolio_id == portfolio_id,
            PositionModel.is_active == True
        ).all()
        
        return sum(Decimal(str(pnl[0])) for pnl in total if pnl[0])
    
    # Standard CRUD interface
    def create(self, entity: PositionEntity) -> PositionEntity:
        """Create new position entity in database (standard CRUD interface)."""
        return self.add(entity)