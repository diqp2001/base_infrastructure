from __future__ import annotations

from datetime import date
from typing import List, Optional, TYPE_CHECKING

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

if TYPE_CHECKING:
    from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding


class Portfolio():
    """
    Pure identification Portfolio.

    Represents a basket / collection of underlying financial assets.
    Can contain various types of holdings including:
    - CompanySharePortfolioHolding (regular company shares)
    - CompanySharePortfolioPortfolioHolding (other portfolios as assets)
    - CompanyShareOptionPortfolioHolding (options)
    - Other holding types
    
    The Portfolio acts as a container for any type of PortfolioHolding.
    Allocation, weights, risk, PnL, etc. live elsewhere (factors/services).
    """

    def __init__(
        self,
        id: int,
        name: str,
        start_date: date,
        end_date: Optional[date] = None,
        holdings: Optional[List['PortfolioHolding']] = None,
    ):
        self.id = id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.holdings = holdings or []

    def add_holding(self, holding: 'PortfolioHolding') -> None:
        """
        Add a holding to this portfolio.
        
        Args:
            holding: Any type of PortfolioHolding (shares, portfolios, options, etc.)
        """
        if holding not in self.holdings:
            self.holdings.append(holding)
    
    def remove_holding(self, holding: 'PortfolioHolding') -> bool:
        """
        Remove a holding from this portfolio.
        
        Args:
            holding: The holding to remove
            
        Returns:
            True if the holding was removed, False if it wasn't found
        """
        if holding in self.holdings:
            self.holdings.remove(holding)
            return True
        return False
    
    def get_holdings_by_type(self, holding_type: str) -> List['PortfolioHolding']:
        """
        Get all holdings of a specific type.
        
        Args:
            holding_type: The class name of the holding type to filter by
            
        Returns:
            List of holdings of the specified type
        """
        return [
            holding for holding in self.holdings
            if holding.__class__.__name__ == holding_type
        ]
    
    def has_holdings(self) -> bool:
        """Check if this portfolio has any holdings."""
        return len(self.holdings) > 0
    
    def holding_count(self) -> int:
        """Get the total number of holdings in this portfolio."""
        return len(self.holdings)

    def __repr__(self) -> str:
        return f"Portfolio(id={self.id}, name='{self.name}', holdings={len(self.holdings)})"
