from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as DomainCompanyStock
from src.infrastructure.models import ModelBase as Base

class CompanyStock(DomainCompanyStock, Base):
    __tablename__ = 'company_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships
    companies = relationship("Company", back_populates="company_stocks")
    exchanges = relationship("Exchange", back_populates="company_stocks")
    key_company_stocks = relationship("KeyCompanyStock", back_populates="company_stock")
    def __init__(self, domain_entity: DomainCompanyStock):
        # Initialize attributes from the domain entity
        super().__init__(
            id=domain_entity.id,
            ticker=domain_entity.ticker,
            exchange_id=domain_entity.exchange_id,
            company_id=domain_entity.company_id,
            start_date=domain_entity.start_date,
            end_date=domain_entity.end_date,
        )
        # You may also set additional infrastructure-related attributes if necessary

    def __repr__(self):
        return f"<CompanyStock(ticker={self.ticker}, company_id={self.company_id})>"

