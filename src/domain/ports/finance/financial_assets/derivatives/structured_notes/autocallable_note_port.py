from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.structured_notes.autocallable_note import AutocallableNote


class AutocallableNotePort(ABC):
    """Port interface for AutocallableNote entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, note_id: int) -> Optional[AutocallableNote]:
        """Retrieve an autocallable note by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[AutocallableNote]:
        """Retrieve all autocallable notes."""
        pass
    
    @abstractmethod
    def get_by_autocall_level(self, min_level: float, max_level: float) -> List[AutocallableNote]:
        """Retrieve autocallable notes by autocall level range."""
        pass
    
    @abstractmethod
    def get_by_observation_frequency(self, frequency: str) -> List[AutocallableNote]:
        """Retrieve autocallable notes by observation frequency."""
        pass
    
    @abstractmethod
    def get_active_notes(self) -> List[AutocallableNote]:
        """Retrieve all active autocallable notes (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, note: AutocallableNote) -> AutocallableNote:
        """Add a new autocallable note."""
        pass
    
    @abstractmethod
    def update(self, note: AutocallableNote) -> AutocallableNote:
        """Update an existing autocallable note."""
        pass
    
    @abstractmethod
    def delete(self, note_id: int) -> bool:
        """Delete an autocallable note by its ID."""
        pass