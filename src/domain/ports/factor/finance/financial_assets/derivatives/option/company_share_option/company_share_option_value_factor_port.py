from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import CompanyShareOptionValueFactor


class CompanyShareOptionValueFactorPort(ABC):
    """Port interface for CompanyShareOptionValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionValueFactor) -> Optional[CompanyShareOptionValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionValueFactor) -> Optional[CompanyShareOptionValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionValueFactor]: ...
