"""
ORM models of the broker order ledger (P.03): broker_orders (one row per internal order sent or about to be sent to a
broker; written BEFORE sending) and broker_executions (one row per broker execution id; unique, so a replayed
execution is never stored or booked twice).
"""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from src.infrastructure.models import ModelBase as Base


class BrokerOrderModel(Base):
    __tablename__ = "broker_orders"
    __table_args__ = (UniqueConstraint("order_id", name="uq_broker_order_order"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    broker = Column(String(50), nullable=False)
    account = Column(String(50), nullable=True)
    portfolio_id = Column(Integer, nullable=True)
    cash_portfolio_id = Column(Integer, nullable=True)
    symbol = Column(String(100), nullable=False)
    side = Column(String(10), nullable=False)
    requested_quantity = Column(Float, nullable=False)
    submission_state = Column(String(20), nullable=False, index=True)
    broker_order_id = Column(Integer, nullable=True, index=True)
    perm_id = Column(Integer, nullable=True, index=True)
    client_id = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    filled_quantity = Column(Float, nullable=False, default=0.0)
    remaining_quantity = Column(Float, nullable=True)
    average_fill_price = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    last_event_at = Column(DateTime, nullable=True)
    cancel_requested_at = Column(DateTime, nullable=True)
    message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (f"<BrokerOrderModel(order={self.order_id}, {self.broker}:{self.broker_order_id}, "
                f"{self.submission_state}, {self.status})>")


class BrokerExecutionModel(Base):
    __tablename__ = "broker_executions"
    __table_args__ = (UniqueConstraint("broker", "exec_id", name="uq_broker_execution"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    exec_id = Column(String(100), nullable=False)
    broker = Column(String(50), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    broker_order_id = Column(Integer, nullable=True)
    perm_id = Column(Integer, nullable=True)
    account = Column(String(50), nullable=True)
    symbol = Column(String(100), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=True)
    commission = Column(Float, nullable=True)
    commission_currency = Column(String(10), nullable=True)
    commission_booked = Column(Boolean, nullable=False, default=False)
    booked = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<BrokerExecutionModel({self.broker}:{self.exec_id}, order={self.order_id}, {self.side} {self.quantity})>"
