from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import CompanyShareOptionImpliedVolFactor


class CompanyShareOptionImpliedVolFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionImpliedVolFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionImpliedVolFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionImpliedVolFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionImpliedVolFactor) -> Optional[CompanyShareOptionImpliedVolFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionImpliedVolFactor) -> Optional[CompanyShareOptionImpliedVolFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionImpliedVolFactor]: ...
