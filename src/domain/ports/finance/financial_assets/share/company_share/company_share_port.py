from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class CompanySharePort(ABC):
    """Port interface for CompanyShare entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, company_share_id: int) -> Optional[CompanyShare]:
    #     """Retrieve a company share by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShare]:
    #     """Retrieve all company shares."""
    #     pass
    
    # @abstractmethod
    # def get_by_company_id(self, company_id: int) -> List[CompanyShare]:
    #     """Retrieve company shares by company ID."""
    #     pass
    
    # @abstractmethod
    # def get_by_exchange_id(self, exchange_id: int) -> List[CompanyShare]:
    #     """Retrieve company shares by exchange ID."""
    #     pass
    
    # @abstractmethod
    # def get_active_company_shares(self) -> List[CompanyShare]:
    #     """Retrieve all active company shares (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, company_share: CompanyShare) -> CompanyShare:
    #     """Add a new company share."""
    #     pass
    
    # @abstractmethod
    # def update(self, company_share: CompanyShare) -> CompanyShare:
    #     """Update an existing company share."""
    #     pass
    
    # @abstractmethod
    # def delete(self, company_share_id: int) -> bool:
    #     """Delete a company share by its ID."""
    #     pass