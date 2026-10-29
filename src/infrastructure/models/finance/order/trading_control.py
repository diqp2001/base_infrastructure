"""
ORM model of the trading controls (P.05): append-only; the latest row per (scope, target) is in force.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text

from src.infrastructure.models import ModelBase as Base


class TradingControlModel(Base):
    __tablename__ = "trading_controls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(20), nullable=False, index=True)
    target = Column(String(200), nullable=False)
    mode = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    changed_by = Column(String(200), nullable=False)
    changed_at = Column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<TradingControlModel({self.scope} {self.target!r} -> {self.mode}, {self.changed_at})>"
