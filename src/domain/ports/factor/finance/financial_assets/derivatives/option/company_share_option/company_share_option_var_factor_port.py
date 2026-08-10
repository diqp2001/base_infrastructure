from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_var_factor import CompanyShareOptionVarFactor


class CompanyShareOptionVarFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionVarFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionVarFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionVarFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionVarFactor) -> Optional[CompanyShareOptionVarFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionVarFactor) -> Optional[CompanyShareOptionVarFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionVarFactor]: ...
