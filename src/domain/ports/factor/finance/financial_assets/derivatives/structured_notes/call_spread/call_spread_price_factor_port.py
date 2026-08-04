from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_price_factor import CallSpreadPriceFactor


class CallSpreadPriceFactorPort(ABC):
    """Port interface for CallSpreadPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadPriceFactor) -> Optional[CallSpreadPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadPriceFactor) -> Optional[CallSpreadPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadPriceFactor]: ...
