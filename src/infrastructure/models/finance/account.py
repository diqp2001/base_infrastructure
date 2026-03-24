from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.account import AccountType, AccountStatus


class AccountModel(Base):
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, unique=True)
    account_type = Column(Enum(AccountType), nullable=False)
    status = Column(Enum(AccountStatus), nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    # Relationships
    currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel",foreign_keys=[currency_id], back_populates="accounts")
    orders = relationship("src.infrastructure.models.finance.order.order.OrderModel", foreign_keys="OrderModel.account_id", back_populates="accounts")
    
    def __repr__(self):
        return f"<Account(id={self.id}, account_id={self.account_id}, type={self.account_type}, status={self.status})>"