from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.structured_notes.structured_note import StructuredNote


class StructuredNotePort(ABC):
    """Port interface for StructuredNote entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, note_id: int) -> Optional[StructuredNote]:
    #     """Retrieve a structured note by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[StructuredNote]:
    #     """Retrieve all structured notes."""
    #     pass
    
    # @abstractmethod
    # def get_by_issuer(self, issuer: str) -> List[StructuredNote]:
    #     """Retrieve structured notes by their issuer."""
    #     pass
    
    # @abstractmethod
    # def get_by_maturity_range(self, start_date: str, end_date: str) -> List[StructuredNote]:
    #     """Retrieve structured notes within a maturity date range."""
    #     pass
    
    # @abstractmethod
    # def get_by_product_type(self, product_type: str) -> List[StructuredNote]:
    #     """Retrieve structured notes by their product type."""
    #     pass
    
    # @abstractmethod
    # def get_active_notes(self) -> List[StructuredNote]:
    #     """Retrieve all active structured notes (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, note: StructuredNote) -> StructuredNote:
    #     """Add a new structured note."""
    #     pass
    
    # @abstractmethod
    # def update(self, note: StructuredNote) -> StructuredNote:
    #     """Update an existing structured note."""
    #     pass
    
    # @abstractmethod
    # def delete(self, note_id: int) -> bool:
    #     """Delete a structured note by its ID."""
    #     pass