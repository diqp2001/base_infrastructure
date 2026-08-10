from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_div_yield_factor import CompanyShareOptionImpliedDivYieldFactor


class CompanyShareOptionImpliedDivYieldFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionImpliedDivYieldFactor) -> Optional[CompanyShareOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionImpliedDivYieldFactor) -> Optional[CompanyShareOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionImpliedDivYieldFactor]: ...
