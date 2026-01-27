"""
Infrastructure model for time series.
SQLAlchemy model for domain time series entity.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean
from sqlalchemy.dialects.postgresql import BYTEA
from src.infrastructure.models import ModelBase as Base
from datetime import datetime


class TimeSeriesModel(Base):
    __tablename__ = 'time_series'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    series_type = Column(String(100), nullable=False)  # financial, ml, dask, etc.
    
    # Store serialized DataFrame data
    data_json = Column(JSON, nullable=True)  # For small series, store as JSON
    data_binary = Column(Boolean, nullable=True)  # For large series, store as pickle/compressed binary
    
    # Metadata
    rows_count = Column(Integer, nullable=True)
    columns_count = Column(Integer, nullable=True)
    columns_info = Column(JSON, nullable=True)  # Store column names and types
    
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    
    
    def __repr__(self):
        return f"<TimeSeries(id={self.id}, name={self.name}, type={self.series_type}, rows={self.rows_count})>"