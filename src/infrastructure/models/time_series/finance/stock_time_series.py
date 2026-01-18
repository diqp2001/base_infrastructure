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
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)
    
    # Relationships  
    stock = relationship("Stock")
    
    __mapper_args__ = {
        'polymorphic_identity': 'stock_time_series',
    }
    
    def __init__(self, name: str, stock_id: int = None, financial_asset_id: int = None,
                 description: str = None, data_json: dict = None, data_binary: bytes = None,
                 rows_count: int = None, columns_count: int = None, columns_info: dict = None):
        super().__init__(
            name=name,
            financial_asset_id=financial_asset_id,
            description=description,
            data_json=data_json,
            data_binary=data_binary,
            rows_count=rows_count,
            columns_count=columns_count,
            columns_info=columns_info
        )
        self.stock_id = stock_id
    
    def __repr__(self):
        return f"<StockTimeSeries(id={self.id}, name={self.name}, stock_id={self.stock_id})>"