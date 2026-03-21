from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.transaction.transaction import TransactionType, TransactionStatus


class TransactionModel(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    holding_id = Column(Integer, ForeignKey('holdings.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    transaction_id = Column(String, nullable=False)
    account_id = Column(String, ForeignKey('accounts.account_id'), nullable=False)
    trade_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=False)
    settlement_date = Column(Date, nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False)
    spread = Column(Float, nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    external_transaction_id = Column(String, nullable=True)
    
    # Relationships
    portfolio = relationship("src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel")
    holding = relationship("src.infrastructure.models.finance.holding.holding.HoldingModel")
    order = relationship("src.infrastructure.models.finance.order.order.OrderModel", back_populates="transactions")
    account = relationship("src.infrastructure.models.finance.account.AccountModel", back_populates="transactions")
    currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel")
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type}, status={self.status}, date={self.date})>"