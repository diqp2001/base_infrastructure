from sqlalchemy import Column, Integer, String, Float, Date
from src.domain.entities.financial_assets.financial_asset import FinancialAsset
from src.infrastructure.database.base import Base  # Import Base from the infrastructure layer



class Stock(FinancialAsset, Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    @property
    def asset_type(self):
        return "Stock"