from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_roll_yield_factor import BondFutureAnnualizedRollYieldFactor


class BondFutureAnnualizedRollYieldFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondFutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondFutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def add(self, entity: BondFutureAnnualizedRollYieldFactor) -> Optional[BondFutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def update(self, entity: BondFutureAnnualizedRollYieldFactor) -> Optional[BondFutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondFutureAnnualizedRollYieldFactor]: ...
