"""
Infrastructure model for time series.
SQLAlchemy model for domain time series entity.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import BYTEA
from src.infrastructure.models import ModelBase as Base
from datetime import datetime


class TimeSeries(Base):
    __tablename__ = 'time_series'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    series_type = Column(String(100), nullable=False)  # financial, ml, dask, etc.
    
    # Store serialized DataFrame data
    data_json = Column(JSON, nullable=True)  # For small series, store as JSON
    data_binary = Column(BYTEA, nullable=True)  # For large series, store as pickle/compressed binary
    
    # Metadata
    rows_count = Column(Integer, nullable=True)
    columns_count = Column(Integer, nullable=True)
    columns_info = Column(JSON, nullable=True)  # Store column names and types
    
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name: str, series_type: str, description: str = None, data_json: dict = None,
                 data_binary: bytes = None, rows_count: int = None, columns_count: int = None,
                 columns_info: dict = None):
        self.name = name
        self.series_type = series_type
        self.description = description
        self.data_json = data_json
        self.data_binary = data_binary
        self.rows_count = rows_count
        self.columns_count = columns_count
        self.columns_info = columns_info
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()
    
    def __repr__(self):
        return f"<TimeSeries(id={self.id}, name={self.name}, type={self.series_type}, rows={self.rows_count})>"