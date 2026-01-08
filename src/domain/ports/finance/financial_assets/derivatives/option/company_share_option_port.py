from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption


class CompanyShareOptionPort(ABC):
    """Port interface for CompanyShareOption entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, option_id: int) -> Optional[CompanyShareOption]:
        """Retrieve a company share option by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[CompanyShareOption]:
        """Retrieve all company share options."""
        pass
    
    @abstractmethod
    def get_by_company_share_id(self, company_share_id: int) -> List[CompanyShareOption]:
        """Retrieve company share options by their underlying company share ID."""
        pass
    
    @abstractmethod
    def get_by_strike_price(self, strike_price: float) -> List[CompanyShareOption]:
        """Retrieve company share options by their strike price."""
        pass
    
    @abstractmethod
    def get_by_expiration_date(self, expiration_date: str) -> List[CompanyShareOption]:
        """Retrieve company share options by their expiration date."""
        pass
    
    @abstractmethod
    def get_active_options(self) -> List[CompanyShareOption]:
        """Retrieve all active company share options (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, option: CompanyShareOption) -> CompanyShareOption:
        """Add a new company share option."""
        pass
    
    @abstractmethod
    def update(self, option: CompanyShareOption) -> CompanyShareOption:
        """Update an existing company share option."""
        pass
    
    @abstractmethod
    def delete(self, option_id: int) -> bool:
        """Delete a company share option by its ID."""
        pass