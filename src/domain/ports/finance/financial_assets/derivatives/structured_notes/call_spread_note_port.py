from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.structured_notes.call_spread_note import CallSpreadNote


class CallSpreadNotePort(ABC):
    """Port interface for CallSpreadNote entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, note_id: int) -> Optional[CallSpreadNote]:
    #     """Retrieve a call spread note by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CallSpreadNote]:
    #     """Retrieve all call spread notes."""
    #     pass
    
    # @abstractmethod
    # def get_by_strike_range(self, min_strike: float, max_strike: float) -> List[CallSpreadNote]:
    #     """Retrieve call spread notes by strike price range."""
    #     pass
    
    # @abstractmethod
    # def get_by_barrier_level(self, barrier_level: float) -> List[CallSpreadNote]:
    #     """Retrieve call spread notes by barrier level."""
    #     pass
    
    # @abstractmethod
    # def get_active_notes(self) -> List[CallSpreadNote]:
    #     """Retrieve all active call spread notes (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, note: CallSpreadNote) -> CallSpreadNote:
    #     """Add a new call spread note."""
    #     pass
    
    # @abstractmethod
    # def update(self, note: CallSpreadNote) -> CallSpreadNote:
    #     """Update an existing call spread note."""
    #     pass
    
    # @abstractmethod
    # def delete(self, note_id: int) -> bool:
    #     """Delete a call spread note by its ID."""
    #     pass