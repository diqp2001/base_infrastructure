"""Domain <-> ORM conversion of the broker order ledger (P.03)."""

from src.domain.entities.finance.order.broker_order import BrokerOrder, Execution, SubmissionState
from src.infrastructure.models.finance.order.broker_order import BrokerExecutionModel, BrokerOrderModel

_ORDER_FIELDS = ("order_id", "broker", "account", "portfolio_id", "cash_portfolio_id", "symbol", "side",
                 "requested_quantity", "broker_order_id", "perm_id", "client_id","status", "filled_quantity", "remaining_quantity", "average_fill_price", "created_at",
                 "submitted_at", "last_event_at", "cancel_requested_at")
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
