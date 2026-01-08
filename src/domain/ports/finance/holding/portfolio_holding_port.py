from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class PortfolioHoldingPort(ABC):
    """Port interface for PortfolioHolding entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, holding_id: int) -> Optional[PortfolioHolding]:
        """Retrieve a portfolio holding by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[PortfolioHolding]:
        """Retrieve all portfolio holdings."""
        pass
    
    @abstractmethod
    def get_by_portfolio(self, portfolio: Portfolio) -> List[PortfolioHolding]:
        """Retrieve holdings by portfolio."""
        pass
    
    @abstractmethod
    def get_by_asset(self, asset: FinancialAsset) -> List[PortfolioHolding]:
        """Retrieve holdings by asset."""
        pass
    
    @abstractmethod
    def get_active_holdings(self) -> List[PortfolioHolding]:
        """Retrieve all active holdings (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, holding: PortfolioHolding) -> PortfolioHolding:
        """Add a new portfolio holding."""
        pass
    
    @abstractmethod
    def update(self, holding: PortfolioHolding) -> PortfolioHolding:
        """Update an existing portfolio holding."""
        pass
    
    @abstractmethod
    def delete(self, holding_id: int) -> bool:
        """Delete a portfolio holding by its ID."""
        pass