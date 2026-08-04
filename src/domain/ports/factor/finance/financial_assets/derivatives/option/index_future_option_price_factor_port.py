from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_price_factor import IndexFutureOptionPriceFactor


class IndexFutureOptionPriceFactorPort(ABC):
    """Port interface for IndexFutureOptionPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFutureOptionPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionPriceFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFutureOptionPriceFactor) -> Optional[IndexFutureOptionPriceFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFutureOptionPriceFactor) -> Optional[IndexFutureOptionPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFutureOptionPriceFactor]: ...
