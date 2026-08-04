from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor


class CompanySharePriceReturnFactorPort(ABC):
    """Port interface for CompanySharePriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePriceReturnFactor) -> Optional[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePriceReturnFactor) -> Optional[CompanySharePriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePriceReturnFactor]: ...
