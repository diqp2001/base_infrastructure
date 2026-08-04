from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_factor import CompanyShareOptionPriceFactor


class CompanyShareOptionPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPriceFactor) -> Optional[CompanyShareOptionPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPriceFactor) -> Optional[CompanyShareOptionPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPriceFactor]: ...
