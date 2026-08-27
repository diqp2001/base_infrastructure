from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_forward_price_factor import BondFutureForwardPriceFactor


class BondFutureForwardPriceFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondFutureForwardPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFutureForwardPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondFutureForwardPriceFactor]: ...

    @abstractmethod
    def add(self, entity: BondFutureForwardPriceFactor) -> Optional[BondFutureForwardPriceFactor]: ...

    @abstractmethod
    def update(self, entity: BondFutureForwardPriceFactor) -> Optional[BondFutureForwardPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondFutureForwardPriceFactor]: ...
