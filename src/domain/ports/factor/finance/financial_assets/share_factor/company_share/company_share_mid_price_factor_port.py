from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor


class CompanyShareMidPriceFactorPort(ABC):
    """Port interface for CompanyShareMidPriceFactor repositories (IBKR leaf factor)."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareMidPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareMidPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareMidPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareMidPriceFactor) -> Optional[CompanyShareMidPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareMidPriceFactor) -> Optional[CompanyShareMidPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareMidPriceFactor]: ...
