from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor import CompanyShareOptionHestonPriceFactor


class CompanyShareOptionHestonPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionHestonPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionHestonPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionHestonPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionHestonPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionHestonPriceFactor) -> Optional[CompanyShareOptionHestonPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionHestonPriceFactor) -> Optional[CompanyShareOptionHestonPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionHestonPriceFactor]: ...
