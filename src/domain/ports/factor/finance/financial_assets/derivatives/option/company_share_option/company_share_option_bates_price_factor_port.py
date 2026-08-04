from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_bates_price_factor import CompanyShareOptionBatesPriceFactor


class CompanyShareOptionBatesPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionBatesPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionBatesPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionBatesPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionBatesPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionBatesPriceFactor) -> Optional[CompanyShareOptionBatesPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionBatesPriceFactor) -> Optional[CompanyShareOptionBatesPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionBatesPriceFactor]: ...
