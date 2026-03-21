from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.account import AccountType, AccountStatus


class AccountModel(Base):
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, nullable=False, unique=True)
    account_type = Column(Enum(AccountType), nullable=False)
    status = Column(Enum(AccountStatus), nullable=False)
    base_currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    # Relationships
    base_currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel")
    orders = relationship("src.infrastructure.models.finance.order.OrderModel", back_populates="account")
    transactions = relationship("src.infrastructure.models.finance.transaction.TransactionModel", back_populates="account")
    
    def __repr__(self):
        return f"<Account(id={self.id}, account_id={self.account_id}, type={self.account_type}, status={self.status})>"