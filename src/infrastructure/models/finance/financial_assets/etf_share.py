"""
ORM model for ETFShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey

from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class ETFShareModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for ETFShare. The fund's holdings are a Universe (UniverseConstituent rows), not columns.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'etf_shares'

    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    issuer = Column(String(100), nullable=True)
    asset_class = Column(String(50), nullable=True)
    leverage_factor = Column(Numeric(precision=8, scale=4), nullable=False, default=1.0)
    replication = Column(String(30), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "ETFShare",
    }

    def __repr__(self):
        return f"<ETFShare(id={self.id}, symbol={self.symbol}, issuer={self.issuer})>"
