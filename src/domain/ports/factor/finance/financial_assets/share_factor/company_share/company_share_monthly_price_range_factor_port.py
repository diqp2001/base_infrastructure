from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_monthly_price_range_factor import CompanyShareMonthlyPriceRangeFactor


class CompanyShareMonthlyPriceRangeFactorPort(ABC):
    """Port interface for CompanyShareMonthlyPriceRangeFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareMonthlyPriceRangeFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareMonthlyPriceRangeFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareMonthlyPriceRangeFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareMonthlyPriceRangeFactor) -> Optional[CompanyShareMonthlyPriceRangeFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareMonthlyPriceRangeFactor) -> Optional[CompanyShareMonthlyPriceRangeFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareMonthlyPriceRangeFactor]: ...
