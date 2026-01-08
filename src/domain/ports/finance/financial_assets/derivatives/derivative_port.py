from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class DerivativePort(ABC):
    """Port interface for Derivative entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, derivative_id: int) -> Optional[Derivative]:
        """Retrieve a derivative by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Derivative]:
        """Retrieve all derivatives."""
        pass
    
    @abstractmethod
    def get_by_underlying_asset(self, underlying_asset: FinancialAsset) -> List[Derivative]:
        """Retrieve derivatives by their underlying asset."""
        pass
    
    @abstractmethod
    def get_active_derivatives(self) -> List[Derivative]:
        """Retrieve all active derivatives (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, derivative: Derivative) -> Derivative:
        """Add a new derivative."""
        pass
    
    @abstractmethod
    def update(self, derivative: Derivative) -> Derivative:
        """Update an existing derivative."""
        pass
    
    @abstractmethod
    def delete(self, derivative_id: int) -> bool:
        """Delete a derivative by its ID."""
        pass