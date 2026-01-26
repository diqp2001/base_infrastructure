"""
ORM model for Financial Asset - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FinancialAssetModel(Base):
    """
    SQLAlchemy ORM model for Financial Asset base class.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'financial_assets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic asset information
    asset_type = Column(String(50), nullable=False, index=True)  # Discriminator for asset type
    name = Column(String(200), nullable=True)
    symbol = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Date information
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    
    __mapper_args__ = {
        "polymorphic_on": asset_type,
        "polymorphic_identity": "financial_asset",
    }
    # Relationships
    instruments = relationship("src.infrastructure.models.finance.instrument.InstrumentModel", back_populates="asset", cascade="all, delete-orphan")
    holdings = relationship("src.infrastructure.models.finance.holding.holding.HoldingModel", back_populates="asset")
    portfolio_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_holding.PortfolioHoldingsModel", back_populates="financial_asset")
    underlying_derivatives = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.derivatives.DerivativeModel",
        foreign_keys="DerivativeModel.underlying_asset_id",
        back_populates="underlying_asset"
    )
    def __repr__(self):
        return f"<FinancialAsset(id={self.id}, type={self.asset_type},)>"