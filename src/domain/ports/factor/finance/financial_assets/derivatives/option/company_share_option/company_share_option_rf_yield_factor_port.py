from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import CompanyShareOptionRFYieldFactor


class CompanyShareOptionRFYieldFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionRFYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionRFYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionRFYieldFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionRFYieldFactor) -> Optional[CompanyShareOptionRFYieldFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionRFYieldFactor) -> Optional[CompanyShareOptionRFYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionRFYieldFactor]: ...
