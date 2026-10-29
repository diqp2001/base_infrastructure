"""
ORM model of the strategy decisions (P.06.05): append-only; broker_orders.decision_id points here.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text

from src.infrastructure.models import ModelBase as Base


class TradingDecisionModel(Base):
    __tablename__ = "trading_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy = Column(String(100), nullable=False, index=True)
    account = Column(String(50), nullable=True)
    bar = Column(DateTime, nullable=False)
    decided_at = Column(DateTime, nullable=False)
    artifact_id = Column(Integer, nullable=True)
    targets = Column(Text, nullable=False)              # JSON {ticker: weight}
    note = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<TradingDecisionModel({self.id} {self.strategy} bar {self.bar})>"
