from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_model_price_factor import CompanyShareOptionModelPriceFactor


class CompanyShareOptionModelPriceFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionModelPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionModelPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionModelPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionModelPriceFactor) -> Optional[CompanyShareOptionModelPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionModelPriceFactor) -> Optional[CompanyShareOptionModelPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionModelPriceFactor]: ...
