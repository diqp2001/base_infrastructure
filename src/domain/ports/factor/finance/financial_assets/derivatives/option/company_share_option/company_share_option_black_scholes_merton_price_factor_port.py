from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import CompanyShareOptionBlackScholesMertonPriceFactor


class CompanyShareOptionBlackScholesMertonPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionBlackScholesMertonPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionBlackScholesMertonPriceFactor) -> Optional[CompanyShareOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionBlackScholesMertonPriceFactor) -> Optional[CompanyShareOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionBlackScholesMertonPriceFactor]: ...
