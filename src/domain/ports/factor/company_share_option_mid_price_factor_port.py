"""
src/domain/ports/factor/company_share_option_mid_price_factor_port.py

Port interface for CompanyShareOptionMidPriceFactor operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor


class CompanyShareOptionMidPriceFactorPort(ABC):
    """Port interface defining contract for CompanyShareOptionMidPriceFactor repository operations."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by ID."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by name."""
        pass

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionMidPriceFactor]:
        """Get all factors."""
        pass

    @abstractmethod
    def add(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Add new factor."""
        pass

    @abstractmethod
    def update(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Update existing factor."""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Delete factor by ID."""
        pass

    @abstractmethod
    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Create new factor or get existing one."""
        pass