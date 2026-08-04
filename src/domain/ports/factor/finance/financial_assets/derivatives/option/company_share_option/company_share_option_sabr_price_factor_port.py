from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_sabr_price_factor import CompanyShareOptionSABRPriceFactor


class CompanyShareOptionSABRPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionSABRPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionSABRPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionSABRPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionSABRPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionSABRPriceFactor) -> Optional[CompanyShareOptionSABRPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionSABRPriceFactor) -> Optional[CompanyShareOptionSABRPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionSABRPriceFactor]: ...
