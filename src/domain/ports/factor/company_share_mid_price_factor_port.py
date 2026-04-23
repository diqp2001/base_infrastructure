"""
src/domain/ports/factor/company_share_mid_price_factor_port.py

Port interface for CompanyShareMidPriceFactor operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor


class CompanyShareMidPriceFactorPort(ABC):
    """Port interface defining contract for CompanyShareMidPriceFactor repository operations."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareMidPriceFactor]:
        """Get factor by ID."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareMidPriceFactor]:
        """Get factor by name."""
        pass

    @abstractmethod
    def get_all(self) -> List[CompanyShareMidPriceFactor]:
        """Get all factors."""
        pass

    @abstractmethod
    def add(self, entity: CompanyShareMidPriceFactor) -> Optional[CompanyShareMidPriceFactor]:
        """Add new factor."""
        pass

    @abstractmethod
    def update(self, entity: CompanyShareMidPriceFactor) -> Optional[CompanyShareMidPriceFactor]:
        """Update existing factor."""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Delete factor by ID."""
        pass

    @abstractmethod
    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanyShareMidPriceFactor]:
        """Create new factor or get existing one."""
        pass