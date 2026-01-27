from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from src.infrastructure.models import ModelBase as Base

class ExchangeModel(Base):
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    legal_name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships
    country = relationship("src.infrastructure.models.country.CountryModel", back_populates="exchanges")
    shares = relationship("src.infrastructure.models.finance.financial_assets.share.ShareModel", back_populates="exchange")
    company_shares = relationship("src.infrastructure.models.finance.financial_assets.company_share.CompanyShareModel", back_populates="exchange")
    etf_shares = relationship("src.infrastructure.models.finance.financial_assets.etf_share.ETFShareModel", back_populates="exchange")
    futures = relationship("src.infrastructure.models.finance.financial_assets.derivative.future.FutureModel", back_populates="exchange")
    
    def __repr__(self):
        return f"<Company(name={self.name}, legal_name={self.legal_name}, start_date={self.start_date}, end_date={self.end_date})>"
