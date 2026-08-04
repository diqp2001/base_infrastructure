from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor import CompanyShareOptionDeltaFactor


class CompanyShareOptionDeltaFactorPort(ABC):
    """Port interface for CompanyShareOptionDeltaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionDeltaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionDeltaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionDeltaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionDeltaFactor) -> Optional[CompanyShareOptionDeltaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionDeltaFactor) -> Optional[CompanyShareOptionDeltaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionDeltaFactor]: ...
