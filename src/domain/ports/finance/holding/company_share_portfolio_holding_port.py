from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHolding


class CompanySharePortfolioHoldingPort(ABC):
    """Port interface for PortfolioCompanyShareHolding entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, holding_id: int) -> Optional[PortfolioCompanyShareHolding]:
    #     """Retrieve a portfolio company share holding by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[PortfolioCompanyShareHolding]:
    #     """Retrieve all portfolio company share holdings."""
    #     pass
    
    # @abstractmethod
    # def get_by_company_share(self, company_share: CompanyShare) -> List[PortfolioCompanyShareHolding]:
    #     """Retrieve holdings by company share."""
    #     pass
    
    # @abstractmethod
    # def get_by_portfolio(self, portfolio: PortfolioCompanyShare) -> List[PortfolioCompanyShareHolding]:
    #     """Retrieve holdings by portfolio."""
    #     pass
    
    # @abstractmethod
    # def get_active_holdings(self) -> List[PortfolioCompanyShareHolding]:
    #     """Retrieve all active holdings (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, holding: PortfolioCompanyShareHolding) -> PortfolioCompanyShareHolding:
    #     """Add a new portfolio company share holding."""
    #     pass
    
    # @abstractmethod
    # def update(self, holding: PortfolioCompanyShareHolding) -> PortfolioCompanyShareHolding:
    #     """Update an existing portfolio company share holding."""
    #     pass
    
    # @abstractmethod
    # def delete(self, holding_id: int) -> bool:
    #     """Delete a portfolio company share holding by its ID."""
    #     pass