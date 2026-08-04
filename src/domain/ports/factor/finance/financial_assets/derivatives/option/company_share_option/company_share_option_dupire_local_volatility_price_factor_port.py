from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_dupire_local_volatility_price_factor import CompanyShareOptionDupireLocalVolatilityPriceFactor


class CompanyShareOptionDupireLocalVolatilityPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionDupireLocalVolatilityPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionDupireLocalVolatilityPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionDupireLocalVolatilityPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionDupireLocalVolatilityPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionDupireLocalVolatilityPriceFactor) -> Optional[CompanyShareOptionDupireLocalVolatilityPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionDupireLocalVolatilityPriceFactor) -> Optional[CompanyShareOptionDupireLocalVolatilityPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionDupireLocalVolatilityPriceFactor]: ...
