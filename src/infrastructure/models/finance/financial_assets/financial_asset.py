"""
ORM model for Financial Asset - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_entity import FinancialEntityModel


class FinancialAssetModel(FinancialEntityModel):
    """
    SQLAlchemy ORM model for Financial Asset base class.
    Joined-table child of FinancialEntityModel — the shared PK root.

    asset_type is kept as an informational column for backward-compatible queries
    but is NO LONGER the SQLAlchemy polymorphic discriminator (entity_type on
    financial_entities is the single discriminator for the full hierarchy).
    New inserts auto-populate asset_type via __init__ to keep existing code working.
    """
    __tablename__ = 'financial_assets'

    id = Column(Integer, ForeignKey('financial_entities.id'), primary_key=True)

    # Informational copy of the polymorphic identity — no longer the ORM discriminator.
    asset_type = Column(String(50), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    symbol = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "financial_asset",
        "inherit_condition": id == FinancialEntityModel.id,
    }

    # instruments relationship stays on FinancialAsset (instruments only link to assets)
    instruments = relationship(
        "src.infrastructure.models.finance.instrument.InstrumentModel",
        back_populates="asset",
        cascade="all, delete-orphan",
    )

    # underlying_derivatives has moved to FinancialEntityModel so portfolios
    # can also serve as underlyings.

    def __init__(self, **kwargs):
        # Mirror entity_type → asset_type so legacy queries on asset_type keep working.
        if 'asset_type' not in kwargs:
            from sqlalchemy import inspect as sa_inspect
            try:
                poly_id = sa_inspect(type(self)).polymorphic_identity
            except Exception:
                poly_id = None
            kwargs['asset_type'] = poly_id or 'financial_asset'
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<FinancialAsset(id={self.id}, type={self.asset_type})>"
