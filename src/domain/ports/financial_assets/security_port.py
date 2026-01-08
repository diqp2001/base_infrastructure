from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.security import Security


class SecurityPort(ABC):
    """Port interface for Security entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, security_id: int) -> Optional[Security]:
        """Retrieve a security by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Security]:
        """Retrieve all securities."""
        pass
    
    @abstractmethod
    def get_active_securities(self) -> List[Security]:
        """Retrieve all active securities (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def get_tradeable_securities(self) -> List[Security]:
        """Retrieve all tradeable securities."""
        pass
    
    @abstractmethod
    def add(self, security: Security) -> Security:
        """Add a new security."""
        pass
    
    @abstractmethod
    def update(self, security: Security) -> Security:
        """Update an existing security."""
        pass
    
    @abstractmethod
    def delete(self, security_id: int) -> bool:
        """Delete a security by its ID."""
        pass