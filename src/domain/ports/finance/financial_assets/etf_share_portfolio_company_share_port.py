from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.share.etf_share_portfolio_company_share import ETFSharePortfolioCompanyShare


class ETFSharePortfolioCompanySharePort(ABC):
    """Port interface for ETFSharePortfolioCompanyShare entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, share_id: int) -> Optional[ETFSharePortfolioCompanyShare]:
        """Retrieve an ETF share portfolio company share by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[ETFSharePortfolioCompanyShare]:
        """Retrieve all ETF share portfolio company shares."""
        pass
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[ETFSharePortfolioCompanyShare]:
        """Retrieve an ETF share portfolio company share by its symbol."""
        pass
    
    @abstractmethod
    def get_by_exchange_id(self, exchange_id: int) -> List[ETFSharePortfolioCompanyShare]:
        """Retrieve ETF share portfolio company shares by exchange ID."""
        pass
    
    @abstractmethod
    def get_by_currency_id(self, currency_id: int) -> List[ETFSharePortfolioCompanyShare]:
        """Retrieve ETF share portfolio company shares by currency ID."""
        pass
    
    @abstractmethod
    def get_by_underlying_asset_id(self, underlying_asset_id: int) -> List[ETFSharePortfolioCompanyShare]:
        """Retrieve ETF share portfolio company shares by underlying asset ID."""
        pass
    
    @abstractmethod
    def add(self, share: ETFSharePortfolioCompanyShare) -> ETFSharePortfolioCompanyShare:
        """Add a new ETF share portfolio company share."""
        pass
    
    @abstractmethod
    def update(self, share: ETFSharePortfolioCompanyShare) -> ETFSharePortfolioCompanyShare:
        """Update an existing ETF share portfolio company share."""
        pass
    
    @abstractmethod
    def delete(self, share_id: int) -> bool:
        """Delete an ETF share portfolio company share by its ID."""
        pass