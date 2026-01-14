from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.portfolio.portfolio import Portfolio


class PortfolioPort(ABC):
    """Port interface for Portfolio entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, portfolio_id: int) -> Optional[Portfolio]:
    #     """Retrieve a portfolio by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Portfolio]:
    #     """Retrieve all portfolios."""
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[Portfolio]:
    #     """Retrieve a portfolio by its name."""
    #     pass
    
    # @abstractmethod
    # def get_active_portfolios(self) -> List[Portfolio]:
    #     """Retrieve all active portfolios (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, portfolio: Portfolio) -> Portfolio:
    #     """Add a new portfolio."""
    #     pass
    
    # @abstractmethod
    # def update(self, portfolio: Portfolio) -> Portfolio:
    #     """Update an existing portfolio."""
    #     pass
    
    # @abstractmethod
    # def delete(self, portfolio_id: int) -> bool:
    #     """Delete a portfolio by its ID."""
    #     pass