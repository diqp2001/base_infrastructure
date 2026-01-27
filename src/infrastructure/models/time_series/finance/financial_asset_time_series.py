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
    
    
    
    def __repr__(self):
        return f"<FinancialAssetTimeSeries(id={self.id}, name={self.name}, asset_id={self.financial_asset_id})>"