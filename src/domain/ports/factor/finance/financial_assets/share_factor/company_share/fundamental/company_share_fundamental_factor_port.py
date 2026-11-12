from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import CompanyShareFundamentalFactor


class CompanyShareFundamentalFactorPort(ABC):
    """Port interface for the calculated company fundamental factor repositories (profitability, leverage, growth,
    valuation)."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareFundamentalFactor) -> Optional[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareFundamentalFactor) -> Optional[CompanyShareFundamentalFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareFundamentalFactor]: ...
