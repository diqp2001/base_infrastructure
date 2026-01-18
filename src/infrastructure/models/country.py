from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base



class CountryModel(Base):
    __tablename__ = 'countries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    iso_code = Column(String(3), nullable=False, unique=True)  # e.g., 'USA', 'CAN'
    region = Column(String(255), nullable=True)  # Optional region classification (e.g., 'North America')
    continent_id = Column(Integer, ForeignKey("continents.id"), nullable=True)

    # Relationships
    continent = relationship("src.infrastructure.models.continent.ContinentModel", back_populates="countries")

    companies = relationship("src.infrastructure.models.finance.company.CompanyModel", back_populates="country")
    exchanges = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="country")
    currencies = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel", back_populates="country")
    def __init__(self, name, iso_code, region=None):
        self.name = name
        self.iso_code = iso_code
        self.region = region

    def __repr__(self):
        return f"<Country(name={self.name}, iso_code={self.iso_code}, region={self.region})>"
