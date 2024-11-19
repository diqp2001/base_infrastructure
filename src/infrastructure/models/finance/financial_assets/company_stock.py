from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as DomainCompanyStock
from infrastructure.database.base_factory import Base

class CompanyStock(DomainCompanyStock, Base):
    __tablename__ = 'company_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    company = relationship("Company", back_populates="company_stocks")
    exchange = relationship("Exchange", back_populates="company_stocks")

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

