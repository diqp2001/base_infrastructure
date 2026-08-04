from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_forward_price_factor import FutureForwardPriceFactor


class FutureForwardPriceFactorPort(ABC):
    """Port interface for FutureForwardPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FutureForwardPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FutureForwardPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FutureForwardPriceFactor]: ...

    @abstractmethod
    def add(self, entity: FutureForwardPriceFactor) -> Optional[FutureForwardPriceFactor]: ...

    @abstractmethod
    def update(self, entity: FutureForwardPriceFactor) -> Optional[FutureForwardPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FutureForwardPriceFactor]: ...
