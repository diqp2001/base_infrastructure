from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_hull_white_price_factor import CompanyShareOptionHullWhitePriceFactor


class CompanyShareOptionHullWhitePriceFactorPort(ABC):
    """Port interface for CompanyShareOptionHullWhitePriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionHullWhitePriceFactor) -> Optional[CompanyShareOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionHullWhitePriceFactor) -> Optional[CompanyShareOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionHullWhitePriceFactor]: ...
