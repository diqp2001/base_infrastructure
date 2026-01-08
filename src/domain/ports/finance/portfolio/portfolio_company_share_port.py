from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare


class PortfolioCompanySharePort(ABC):
    """Port interface for PortfolioCompanyShare entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, portfolio_id: int) -> Optional[PortfolioCompanyShare]:
        """Retrieve a company share portfolio by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[PortfolioCompanyShare]:
        """Retrieve all company share portfolios."""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShare]:
        """Retrieve a company share portfolio by its name."""
        pass
    
    @abstractmethod
    def get_active_portfolios(self) -> List[PortfolioCompanyShare]:
        """Retrieve all active company share portfolios (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, portfolio: PortfolioCompanyShare) -> PortfolioCompanyShare:
        """Add a new company share portfolio."""
        pass
    
    @abstractmethod
    def update(self, portfolio: PortfolioCompanyShare) -> PortfolioCompanyShare:
        """Update an existing company share portfolio."""
        pass
    
    @abstractmethod
    def delete(self, portfolio_id: int) -> bool:
        """Delete a company share portfolio by its ID."""
        pass