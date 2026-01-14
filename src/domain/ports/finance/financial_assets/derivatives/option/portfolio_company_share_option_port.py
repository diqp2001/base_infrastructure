from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option import PortfolioCompanyShareOption


class PortfolioCompanyShareOptionPort(ABC):
    """Port interface for PortfolioCompanyShareOption entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, option_id: int) -> Optional[PortfolioCompanyShareOption]:
    #     """Retrieve a portfolio company share option by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[PortfolioCompanyShareOption]:
    #     """Retrieve all portfolio company share options."""
    #     pass
    
    # @abstractmethod
    # def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioCompanyShareOption]:
    #     """Retrieve portfolio company share options by portfolio ID."""
    #     pass
    
    # @abstractmethod
    # def get_by_company_share_id(self, company_share_id: int) -> List[PortfolioCompanyShareOption]:
    #     """Retrieve portfolio company share options by their underlying company share ID."""
    #     pass
    
    # @abstractmethod
    # def get_active_options(self) -> List[PortfolioCompanyShareOption]:
    #     """Retrieve all active portfolio company share options (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, option: PortfolioCompanyShareOption) -> PortfolioCompanyShareOption:
    #     """Add a new portfolio company share option."""
    #     pass
    
    # @abstractmethod
    # def update(self, option: PortfolioCompanyShareOption) -> PortfolioCompanyShareOption:
    #     """Update an existing portfolio company share option."""
    #     pass
    
    # @abstractmethod
    # def delete(self, option_id: int) -> bool:
    #     """Delete a portfolio company share option by its ID."""
    #     pass