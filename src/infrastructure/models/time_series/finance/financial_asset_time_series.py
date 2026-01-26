"""
Infrastructure model for financial asset time series.
SQLAlchemy model for domain financial asset time series entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.time_series.time_series import TimeSeriesModel


class FinancialAssetTimeSeriesModel(TimeSeriesModel):
    __tablename__ = 'financial_asset_time_series'
    
    id = Column(Integer, ForeignKey("time_series.id"), primary_key=True)
    financial_asset_id = Column(Integer,nullable=True)
    
    
    
    __mapper_args__ = {
        'polymorphic_identity': 'financial_asset_time_series',
        'inherit_condition': id == TimeSeriesModel.id
    }
    
    def __init__(self, name: str,  description: str = None,
                 data_json: dict = None, data_binary: bytes = None, rows_count: int = None, 
                 columns_count: int = None, columns_info: dict = None):
        super().__init__(
            name=name, 
            series_type='financial_asset_time_series', 
            description=description,
            data_json=data_json,
            data_binary=data_binary,
            rows_count=rows_count,
            columns_count=columns_count,
            columns_info=columns_info
        )
    
    def __repr__(self):
        return f"<FinancialAssetTimeSeries(id={self.id}, name={self.name}, asset_id={self.financial_asset_id})>"