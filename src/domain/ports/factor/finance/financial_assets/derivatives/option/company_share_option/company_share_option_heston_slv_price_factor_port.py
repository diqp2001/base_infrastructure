from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_slv_price_factor import CompanyShareOptionHestonSLVPriceFactor


class CompanyShareOptionHestonSLVPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionHestonSLVPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionHestonSLVPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionHestonSLVPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionHestonSLVPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionHestonSLVPriceFactor) -> Optional[CompanyShareOptionHestonSLVPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionHestonSLVPriceFactor) -> Optional[CompanyShareOptionHestonSLVPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionHestonSLVPriceFactor]: ...
