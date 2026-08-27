from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_yield_factor import BondFutureAnnualizedYieldFactor


class BondFutureAnnualizedYieldFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondFutureAnnualizedYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFutureAnnualizedYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondFutureAnnualizedYieldFactor]: ...

    @abstractmethod
    def add(self, entity: BondFutureAnnualizedYieldFactor) -> Optional[BondFutureAnnualizedYieldFactor]: ...

    @abstractmethod
    def update(self, entity: BondFutureAnnualizedYieldFactor) -> Optional[BondFutureAnnualizedYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondFutureAnnualizedYieldFactor]: ...
