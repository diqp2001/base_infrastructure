from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vol_factor import CompanyShareOptionVolFactor


class CompanyShareOptionVolFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionVolFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionVolFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionVolFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionVolFactor) -> Optional[CompanyShareOptionVolFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionVolFactor) -> Optional[CompanyShareOptionVolFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionVolFactor]: ...
