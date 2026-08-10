"""
ORM model for FinancialEntity — the common root for FinancialAsset and Portfolio.

Why this exists
---------------
DerivativeModel.underlying_asset_id previously pointed at financial_assets.id, which
made it impossible for a CompanySharePortfolioOption to reference its underlying
CompanySharePortfolio (a Portfolio, not a FinancialAsset).

HoldingModel.asset_id previously had no FK at all; each concrete holding subclass
declared its own child-table column aliased to 'asset_id' and used column_property
to merge the two — an anti-pattern that this root table eliminates.

Solution: both FinancialAssetModel and PortfolioModel now join their PK to
financial_entities.id.  DerivativeModel.underlying_asset_id and HoldingModel.asset_id
both FK to financial_entities.id, so any financial entity (asset or portfolio) can
serve as an underlying or an asset in a holding.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FinancialEntityModel(Base):
    """
    Root table that provides a shared PK space for FinancialAsset and Portfolio.

    SQLAlchemy joined-table inheritance root:
      - entity_type is the single discriminator for the entire hierarchy.
      - FinancialAssetModel and PortfolioModel each add a child table row
        whose 'id' FK references this table's PK.
      - All leaf polymorphic_identity values (e.g. 'company_share', 'Portfolio',
        'CompanySharePortfolio') now map to financial_entities.entity_type.
    """
    __tablename__ = 'financial_entities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False, index=True)

    __mapper_args__ = {
        "polymorphic_on": entity_type,
        "polymorphic_identity": "financial_entity",
    }

    # Any derivative whose underlying is this entity (asset or portfolio).
    # back_populates targets DerivativeModel.underlying_asset (name kept for compat).
    underlying_derivatives = relationship(
        "src.infrastructure.models.finance.financial_assets.derivative.derivatives.DerivativeModel",
        foreign_keys="[src.infrastructure.models.finance.financial_assets.derivative.derivatives.DerivativeModel.underlying_asset_id]",
        back_populates="underlying_asset",
    )
