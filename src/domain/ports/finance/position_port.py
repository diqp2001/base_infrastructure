from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.holding.position import Position, PositionType


class PositionPort(ABC):
    """Port interface for Position entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, position_id: int) -> Optional[Position]:
    #     """Retrieve a position by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Position]:
    #     """Retrieve all positions."""
    #     pass
    
    # @abstractmethod
    # def get_by_position_type(self, position_type: PositionType) -> List[Position]:
    #     """Retrieve positions by position type (LONG/SHORT)."""
    #     pass
    
    # @abstractmethod
    # def get_by_quantity_range(self, min_quantity: int, max_quantity: int) -> List[Position]:
    #     """Retrieve positions within a quantity range."""
    #     pass
    
    # @abstractmethod
    # def add(self, position: Position) -> Position:
    #     """Add a new position."""
    #     pass
    
    # @abstractmethod
    # def update(self, position: Position) -> Position:
    #     """Update an existing position."""
    #     pass
    
    # @abstractmethod
    # def delete(self, position_id: int) -> bool:
    #     """Delete a position by its ID."""
    #     pass