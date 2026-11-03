"""
Local SQLAlchemy repositories of the broker order ledger (P.03).

They raise on failure (after rolling back) instead of returning None: an order intent or an execution that was not
stored must never look stored. Inside ``atomic(session)`` their commit is a flush, so they join the caller's
transaction.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.finance.order.broker_order import BrokerOrder, Execution, SubmissionState
from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind
from src.domain.ports.finance.broker_order_port import (
    BrokerOrderPort,
    CashSnapshotPort,
    DiscrepancyPort,
    ExecutionPort,
    TradingControlPort,
    TradingDecisionPort,
)
from src.infrastructure.models.finance.order.broker_order import (
    BrokerExecutionModel,
    BrokerOrderModel,
    TradingDiscrepancyModel,
)
from src.infrastructure.models.finance.order.cash_snapshot import CashSnapshotModel
from src.infrastructure.models.finance.order.order import OrderModel
from src.infrastructure.models.finance.order.trading_control import TradingControlModel
from src.infrastructure.models.finance.order.trading_decision import TradingDecisionModel
from src.infrastructure.repositories.mappers.finance.order.broker_order_mapper import (
    BrokerOrderMapper,
    CashSnapshotMapper,
    DiscrepancyMapper,
    ExecutionMapper,
    TradingControlMapper,
    TradingDecisionMapper,
)

OPEN_STATUSES = ("PENDING", "SUBMITTED", "PARTIALLY_FILLED")


class _Base:
    model_class = None
    mapper = None

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory

    def _row(self, id: int):
        return self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()

    def _save(self, entity, orm):
        try:
            self.mapper.copy_to_orm(entity, orm)
            self.session.add(orm)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        entity.id = orm.id
        return entity

    def get_by_id(self, id: int):
        return self.mapper.to_domain(self._row(id))

    def get_all(self) -> list:
        return [self.mapper.to_domain(r) for r in self.session.query(self.model_class)
                .order_by(self.model_class.id).all()]

    def add(self, entity):
        return self._save(entity, self.model_class())

    def update(self, entity):
        orm = self._row(entity.id) if entity.id is not None else None
        if orm is None:
            raise LookupError(f"{type(entity).__name__} {entity.id} does not exist")
        return self._save(entity, orm)


class BrokerOrderRepository(_Base, BrokerOrderPort):
    model_class = BrokerOrderModel
    mapper = BrokerOrderMapper

    def get_by_order_id(self, order_id: int) -> Optional[BrokerOrder]:
        return self.mapper.to_domain(self.session.query(BrokerOrderModel)
                                     .filter(BrokerOrderModel.order_id == order_id).one_or_none())

    def get_by_broker_order_id(self, broker: str, broker_order_id: int,
                               client_id: Optional[int] = None) -> Optional[BrokerOrder]:
        q = self.session.query(BrokerOrderModel).filter(BrokerOrderModel.broker == broker,
                                                        BrokerOrderModel.broker_order_id == broker_order_id)
        if client_id is not None:
            q = q.filter(BrokerOrderModel.client_id == client_id)
        rows = q.order_by(BrokerOrderModel.id.desc()).all()
        return self.mapper.to_domain(rows[0]) if rows else None

    def get_by_perm_id(self, broker: str, perm_id: int) -> Optional[BrokerOrder]:
        return self.mapper.to_domain(self.session.query(BrokerOrderModel).filter(
            BrokerOrderModel.broker == broker, BrokerOrderModel.perm_id == perm_id).one_or_none())

    def get_open(self) -> List[BrokerOrder]:
        rows = (self.session.query(BrokerOrderModel)
                .filter(BrokerOrderModel.status.in_(OPEN_STATUSES)
                        | (BrokerOrderModel.submission_state == SubmissionState.UNKNOWN.value))
                .order_by(BrokerOrderModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    def mirror_to_order(self, entity: BrokerOrder) -> None:
        row = self.session.query(OrderModel).filter(OrderModel.id == entity.order_id).one_or_none()
        if row is None:
            raise LookupError(f"order {entity.order_id} does not exist")
        try:
            row.status = entity.status
            row.filled_quantity = entity.filled_quantity
            row.average_fill_price = entity.average_fill_price
            if entity.broker_order_id is not None:
                row.external_order_id = f"{entity.broker}:{entity.broker_order_id}"
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise


class ExecutionRepository(_Base, ExecutionPort):
    model_class = BrokerExecutionModel
    mapper = ExecutionMapper

    def get_by_exec_id(self, broker: str, exec_id: str) -> Optional[Execution]:
        return self.mapper.to_domain(self.session.query(BrokerExecutionModel).filter(
            BrokerExecutionModel.broker == broker, BrokerExecutionModel.exec_id == exec_id).one_or_none())

    def get_by_order_id(self, order_id: int) -> List[Execution]:
        rows = (self.session.query(BrokerExecutionModel).filter(BrokerExecutionModel.order_id == order_id)
                .order_by(BrokerExecutionModel.executed_at, BrokerExecutionModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    def get_unexplained(self) -> List[Execution]:
        rows = (self.session.query(BrokerExecutionModel).filter(BrokerExecutionModel.order_id.is_(None))
                .order_by(BrokerExecutionModel.executed_at).all())
        return [self.mapper.to_domain(r) for r in rows]


class DiscrepancyRepository(_Base, DiscrepancyPort):
    model_class = TradingDiscrepancyModel
    mapper = DiscrepancyMapper

    def get_open(self, kind: Optional[DiscrepancyKind] = None) -> List[Discrepancy]:
        q = self.session.query(TradingDiscrepancyModel).filter(TradingDiscrepancyModel.resolved_at.is_(None))
        if kind is not None:
            q = q.filter(TradingDiscrepancyModel.kind == kind.value)
        return [self.mapper.to_domain(r) for r in q.order_by(TradingDiscrepancyModel.id).all()]

    def get_open_by_key(self, kind: DiscrepancyKind, key: str) -> Optional[Discrepancy]:
        rows = (self.session.query(TradingDiscrepancyModel)
                .filter(TradingDiscrepancyModel.resolved_at.is_(None), TradingDiscrepancyModel.kind == kind.value,
                        TradingDiscrepancyModel.key == key).order_by(TradingDiscrepancyModel.id).all())
        return self.mapper.to_domain(rows[0]) if rows else None

    def get_latest_by_key(self, kind: DiscrepancyKind, key: str) -> Optional[Discrepancy]:
        row = (self.session.query(TradingDiscrepancyModel)
               .filter(TradingDiscrepancyModel.kind == kind.value, TradingDiscrepancyModel.key == key)
               .order_by(TradingDiscrepancyModel.id.desc()).first())
        return self.mapper.to_domain(row)


class TradingControlRepository(_Base, TradingControlPort):
    """Append-only: a control changes by adding a row, never by updating one (the history is the audit trail)."""
    model_class = TradingControlModel
    mapper = TradingControlMapper

    def update(self, entity):
        raise NotImplementedError("trading controls are append-only: add a new row")


class TradingDecisionRepository(_Base, TradingDecisionPort):
    """Append-only: a decision is what the strategy asked for at a bar; it is never rewritten."""
    model_class = TradingDecisionModel
    mapper = TradingDecisionMapper

    def update(self, entity):
        raise NotImplementedError("trading decisions are append-only")

    def get_recent(self, strategy: str, limit: int = 50):
        rows = (self.session.query(TradingDecisionModel).filter(TradingDecisionModel.strategy == strategy)
                .order_by(TradingDecisionModel.id.desc()).limit(limit).all())
        return [self.mapper.to_domain(r) for r in rows]


class CashSnapshotRepository(_Base, CashSnapshotPort):
    """Append-only: a snapshot is what the broker and the books held when it was taken."""
    model_class = CashSnapshotModel
    mapper = CashSnapshotMapper

    def update(self, entity):
        raise NotImplementedError("cash snapshots are append-only")

    def get_latest(self, account: str):
        return self.mapper.to_domain(self.session.query(CashSnapshotModel).filter(CashSnapshotModel.account == account)
                                     .order_by(CashSnapshotModel.id.desc()).first())

    def get_recent(self, account: str, limit: int = 30):
        rows = (self.session.query(CashSnapshotModel).filter(CashSnapshotModel.account == account)
                .order_by(CashSnapshotModel.id.desc()).limit(limit).all())
        return [self.mapper.to_domain(r) for r in rows]
