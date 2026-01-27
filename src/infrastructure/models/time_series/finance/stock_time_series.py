"""
Infrastructure model for stock time series.
SQLAlchemy model for domain stock time series entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeriesModel


class StockTimeSeriesModel(FinancialAssetTimeSeriesModel):
    __tablename__ = 'stock_time_series'
    
    id = Column(Integer, ForeignKey("financial_asset_time_series.id"), primary_key=True)
    
    
    
    
    __mapper_args__ = {
        'polymorphic_identity': 'stock_time_series',
    }
    
    
    
    def __repr__(self):
        return f"<StockTimeSeries(id={self.id}, name={self.name})>"