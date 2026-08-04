from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_price_return_factor import IndexFutureOptionPriceReturnFactor


class IndexFutureOptionPriceReturnFactorPort(ABC):
    """Port interface for IndexFutureOptionPriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFutureOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexFutureOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionPriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFutureOptionPriceReturnFactor) -> Optional[IndexFutureOptionPriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFutureOptionPriceReturnFactor) -> Optional[IndexFutureOptionPriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFutureOptionPriceReturnFactor]: ...
