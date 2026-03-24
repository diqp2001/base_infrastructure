from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.order.order import OrderType, OrderSide, OrderStatus


class OrderModel(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    holding_id = Column(Integer, ForeignKey('holdings.id'), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.account_id'), nullable=False)
    price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    filled_quantity = Column(Float, nullable=False, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    time_in_force = Column(String, nullable=True)
    external_order_id = Column(String, nullable=True)
    
    # Relationships
    holdings = relationship("src.infrastructure.models.finance.holding.holding.HoldingModel",foreign_keys=[holding_id], back_populates="orders")#knows the portfolio
    accounts = relationship("src.infrastructure.models.finance.account.AccountModel",foreign_keys=[account_id], back_populates="orders")
    transactions = relationship("src.infrastructure.models.finance.transaction.transaction.TransactionModel", foreign_keys="TransactionModel.order_id", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.id}, side={self.side}, type={self.order_type}, status={self.status}, quantity={self.quantity})>"