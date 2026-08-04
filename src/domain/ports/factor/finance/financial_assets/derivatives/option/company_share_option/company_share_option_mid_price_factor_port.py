from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor


class CompanyShareOptionMidPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionMidPriceFactor repositories (IBKR leaf factor for option mid price)."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionMidPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionMidPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionMidPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionMidPriceFactor]: ...
