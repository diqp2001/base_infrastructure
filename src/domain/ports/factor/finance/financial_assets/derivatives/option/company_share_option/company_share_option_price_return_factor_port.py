from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor


class CompanyShareOptionPriceReturnFactorPort(ABC):
    """Port interface for CompanyShareOptionPriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanyShareOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPriceReturnFactor) -> Optional[CompanyShareOptionPriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPriceReturnFactor) -> Optional[CompanyShareOptionPriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPriceReturnFactor]: ...
