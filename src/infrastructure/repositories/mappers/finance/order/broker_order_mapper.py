"""Domain <-> ORM conversion of the broker order ledger (P.03)."""

import json

from src.domain.entities.finance.order.broker_order import BrokerOrder, Execution, SubmissionState
from src.domain.entities.finance.order.cash_snapshot import CashSnapshot
from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind
from src.domain.entities.finance.order.trading_control import ControlMode, ControlScope, TradingControl
from src.domain.entities.finance.order.trading_decision import TradingDecision
from src.infrastructure.models.finance.order.broker_order import (
    BrokerExecutionModel,
    BrokerOrderModel,
    TradingDiscrepancyModel,
)
from src.infrastructure.models.finance.order.cash_snapshot import CashSnapshotModel
from src.infrastructure.models.finance.order.trading_control import TradingControlModel
from src.infrastructure.models.finance.order.trading_decision import TradingDecisionModel

_ORDER_FIELDS = ("order_id", "broker", "account", "portfolio_id", "cash_portfolio_id", "symbol", "side",
                 "requested_quantity", "broker_order_id", "perm_id", "client_id","status", "filled_quantity", "remaining_quantity", "average_fill_price", "created_at",
                 "submitted_at", "last_event_at", "cancel_requested_at", "decision_id")
_EXECUTION_FIELDS = ("exec_id", "broker", "order_id", "broker_order_id", "perm_id", "account", "symbol", "side",
                     "quantity", "price", "executed_at", "received_at", "commission", "commission_currency",
                     "commission_booked", "booked")


class BrokerOrderMapper:

    @staticmethod
    def to_domain(orm: BrokerOrderModel):
        if orm is None:
            return None
        values = {f: getattr(orm, f) for f in _ORDER_FIELDS}
        return BrokerOrder(id=orm.id, submission_state=SubmissionState(orm.submission_state),
                           message=orm.message or "", **values)

    @staticmethod
    def copy_to_orm(entity: BrokerOrder, orm: BrokerOrderModel) -> BrokerOrderModel:
        for f in _ORDER_FIELDS:
            setattr(orm, f, getattr(entity, f))
        orm.submission_state = entity.submission_state.value
        orm.message = entity.message or None
        return orm


class ExecutionMapper:

    @staticmethod
    def to_domain(orm: BrokerExecutionModel):
        if orm is None:
            return None
        values = {f: getattr(orm, f) for f in _EXECUTION_FIELDS}
        values["commission_booked"] = bool(values["commission_booked"])
        values["booked"] = bool(values["booked"])
        return Execution(id=orm.id, notes=orm.notes or "", **values)

    @staticmethod
    def copy_to_orm(entity: Execution, orm: BrokerExecutionModel) -> BrokerExecutionModel:
        for f in _EXECUTION_FIELDS:
            setattr(orm, f, getattr(entity, f))
        orm.notes = entity.notes or None
        return orm


_DISCREPANCY_FIELDS = ("key", "broker", "order_id", "detail", "detected_at", "resolved_at", "resolution")


class DiscrepancyMapper:

    @staticmethod
    def to_domain(orm: TradingDiscrepancyModel):
        if orm is None:
            return None
        values = {f: getattr(orm, f) for f in _DISCREPANCY_FIELDS}
        return Discrepancy(id=orm.id, kind=DiscrepancyKind(orm.kind), blocking=bool(orm.blocking), **values)

    @staticmethod
    def copy_to_orm(entity: Discrepancy, orm: TradingDiscrepancyModel) -> TradingDiscrepancyModel:
        for f in _DISCREPANCY_FIELDS:
            setattr(orm, f, getattr(entity, f))
        orm.kind = entity.kind.value
        orm.blocking = bool(entity.blocking)
        return orm


class TradingControlMapper:

    @staticmethod
    def to_domain(orm: TradingControlModel):
        if orm is None:
            return None
        return TradingControl(scope=ControlScope(orm.scope), target=orm.target, mode=ControlMode(orm.mode),
                              reason=orm.reason, changed_by=orm.changed_by, changed_at=orm.changed_at, id=orm.id)

    @staticmethod
    def copy_to_orm(entity: TradingControl, orm: TradingControlModel) -> TradingControlModel:
        orm.scope, orm.target, orm.mode = entity.scope.value, entity.target, entity.mode.value
        orm.reason, orm.changed_by, orm.changed_at = entity.reason, entity.changed_by, entity.changed_at
        return orm


class TradingDecisionMapper:

    @staticmethod
    def to_domain(orm: TradingDecisionModel):
        if orm is None:
            return None
        return TradingDecision(strategy=orm.strategy, bar=orm.bar, decided_at=orm.decided_at,
                               targets={k: float(v) for k, v in json.loads(orm.targets or "{}").items()},
                               account=orm.account, artifact_id=orm.artifact_id, note=orm.note or "", id=orm.id)

    @staticmethod
    def copy_to_orm(entity: TradingDecision, orm: TradingDecisionModel) -> TradingDecisionModel:
        orm.strategy, orm.account, orm.bar, orm.decided_at = entity.strategy, entity.account, entity.bar, \
            entity.decided_at
        orm.artifact_id, orm.note = entity.artifact_id, entity.note or None
        orm.targets = json.dumps({k: float(v) for k, v in entity.targets.items()}, sort_keys=True)
        return orm


_CASH_SNAPSHOT_FIELDS = ("account", "portfolio_id", "taken_at", "currency", "broker_cash", "book_cash", "broker_change",
                         "book_change", "booked", "unexplained", "transaction_ref")


class CashSnapshotMapper:

    @staticmethod
    def to_domain(orm: CashSnapshotModel):
        if orm is None:
            return None
        return CashSnapshot(**{f: getattr(orm, f) for f in _CASH_SNAPSHOT_FIELDS}, note=orm.note or "", id=orm.id)

    @staticmethod
    def copy_to_orm(entity: CashSnapshot, orm: CashSnapshotModel) -> CashSnapshotModel:
        for f in _CASH_SNAPSHOT_FIELDS:
            setattr(orm, f, getattr(entity, f))
        orm.note = entity.note or None
        return orm
