"""
ORM model of the daily cash snapshots, broker vs books (P.04.04 / P.06.13): append-only.
"""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from src.infrastructure.models import ModelBase as Base


class CashSnapshotModel(Base):
    __tablename__ = "cash_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(50), nullable=False, index=True)
    portfolio_id = Column(Integer, nullable=False)
    taken_at = Column(DateTime, nullable=False)
    currency = Column(String(10), nullable=False)
    broker_cash = Column(Float, nullable=False)
    book_cash = Column(Float, nullable=False)
    broker_change = Column(Float, nullable=True)
    book_change = Column(Float, nullable=True)
    booked = Column(Float, nullable=False, default=0.0)
    unexplained = Column(Float, nullable=False, default=0.0)
    transaction_ref = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<CashSnapshotModel({self.account} {self.taken_at} broker {self.broker_cash} book {self.book_cash})>"
