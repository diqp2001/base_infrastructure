from sqlalchemy import Column, Integer, String, Float, Date
from src.domain.entities.financial_assets.stock import Stock
from src.infrastructure.database.base import Base  # Import Base from the infrastructure layer


"""Represents how the entity is stored in the database (tables, columns)."""
class Stock(Stock, Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    @property
    def asset_type(self):
        return "Stock"