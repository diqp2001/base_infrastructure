"""Ports of the broker order ledger: broker-side orders and executions (P.03)."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.finance.order.broker_order import BrokerOrder, Execution
from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind


class BrokerOrderPort(ABC):

    @abstractmethod
    def add(self, entity: BrokerOrder) -> BrokerOrder: ...

    @abstractmethod
    def update(self, entity: BrokerOrder) -> BrokerOrder: ...

    @abstractmethod
    def get_by_order_id(self, order_id: int) -> Optional[BrokerOrder]: ...

    @abstractmethod
    def get_by_broker_order_id(self, broker: str, broker_order_id: int,
                               client_id: Optional[int] = None) -> Optional[BrokerOrder]: ...

    @abstractmethod
    def get_by_perm_id(self, broker: str, perm_id: int) -> Optional[BrokerOrder]: ...

    @abstractmethod
    def get_open(self) -> List[BrokerOrder]: ...

    @abstractmethod
    def mirror_to_order(self, entity: BrokerOrder) -> None:
        """Copy status, filled quantity, average price and broker id onto the internal order it belongs to."""


class ExecutionPort(ABC):

    @abstractmethod
    def add(self, entity: Execution) -> Execution: ...

    @abstractmethod
    def update(self, entity: Execution) -> Execution: ...

    @abstractmethod
    def get_by_exec_id(self, broker: str, exec_id: str) -> Optional[Execution]: ...

    @abstractmethod
    def get_by_order_id(self, order_id: int) -> List[Execution]: ...

    @abstractmethod
    def get_unexplained(self) -> List[Execution]: ...


class DiscrepancyPort(ABC):
    """Recovery discrepancies (P.04): one OPEN row per (kind, key)."""

    @abstractmethod
    def add(self, entity: Discrepancy) -> Discrepancy: ...

    @abstractmethod
    def update(self, entity: Discrepancy) -> Discrepancy: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Discrepancy]: ...

    @abstractmethod
    def get_open(self, kind: Optional[DiscrepancyKind] = None) -> List[Discrepancy]: ...

    @abstractmethod
    def get_open_by_key(self, kind: DiscrepancyKind, key: str) -> Optional[Discrepancy]: ...

    @abstractmethod
    def get_latest_by_key(self, kind: DiscrepancyKind, key: str) -> Optional[Discrepancy]:
        """The most recent discrepancy of that kind and key, open or resolved."""
