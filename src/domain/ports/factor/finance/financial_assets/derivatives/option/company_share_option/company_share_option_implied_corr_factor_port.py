from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_corr_factor import CompanyShareOptionImpliedCorrFactor


class CompanyShareOptionImpliedCorrFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionImpliedCorrFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionImpliedCorrFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionImpliedCorrFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionImpliedCorrFactor) -> Optional[CompanyShareOptionImpliedCorrFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionImpliedCorrFactor) -> Optional[CompanyShareOptionImpliedCorrFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionImpliedCorrFactor]: ...
