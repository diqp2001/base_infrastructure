from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor import CompanyShareOptionVegaFactor


class CompanyShareOptionVegaFactorPort(ABC):
    """Port interface for CompanyShareOptionVegaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionVegaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionVegaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionVegaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionVegaFactor) -> Optional[CompanyShareOptionVegaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionVegaFactor) -> Optional[CompanyShareOptionVegaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionVegaFactor]: ...
