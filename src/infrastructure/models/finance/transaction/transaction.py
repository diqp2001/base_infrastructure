from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.transaction.transaction import TransactionType, TransactionStatus


class TransactionModel(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    transaction_id = Column(String, nullable=False)
    trade_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=False)
    settlement_date = Column(Date, nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False)
    spread = Column(Float, nullable=False)
    external_transaction_id = Column(String, nullable=True)
    
    order = relationship("src.infrastructure.models.finance.order.order.OrderModel",foreign_keys=[order_id], back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type}, status={self.status}, date={self.date})>"