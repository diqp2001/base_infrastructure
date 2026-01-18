"""
SQLAlchemy model for Instrument entity.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from src.infrastructure.models import ModelBase as Base


class InstrumentModel(Base):
    """SQLAlchemy model for Instrument entity."""
    
    __tablename__ = 'instruments'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to FinancialAsset
    asset_id = Column(Integer, ForeignKey("financial_assets.id"), nullable=False)
    
    # Core attributes
    source = Column(String(255), nullable=False)  # Data source (e.g., 'Bloomberg', 'Reuters')
    date = Column(DateTime, nullable=False)  # Date when instrument data was recorded
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    asset = relationship("src.infrastructure.models.finance.financial_assets.financial_asset.FinancialAssetModel", back_populates="instruments")
    
    def __init__(self, asset_id: int, source: str, date: datetime):
        """
        Initialize Instrument model.
        
        Args:
            asset_id: ID of the associated FinancialAsset
            source: Data source name
            date: Date of the instrument data
        """
        self.asset_id = asset_id
        self.source = source
        self.date = date
    
    def __repr__(self):
        return (
            f"<Instrument(id={self.id}, asset_id={self.asset_id}, "
            f"source={self.source}, date={self.date})>"
        )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'source': self.source,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }