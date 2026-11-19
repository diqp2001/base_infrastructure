"""
src/infrastructure/models/universe/universe_financial_asset.py

SQLAlchemy ORM model for UniverseFinancialAsset. Table: universe_financial_assets.
Membership only (no weight / rank). A membership is unique per (universe, asset, start_date); overlapping windows
of the same asset are refused by the Universe entity and the repository (start_date may be NULL, which databases
compare differently in unique constraints).
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class UniverseFinancialAssetModel(Base):
    __tablename__ = "universe_financial_assets"
    __table_args__ = (
        UniqueConstraint("universe_id", "financial_asset_id", "start_date", name="uq_universe_financial_asset"),
    )

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    universe_id        = Column(Integer, ForeignKey("universes.id"), nullable=False, index=True)
    financial_asset_id = Column(Integer, ForeignKey("financial_assets.id"), nullable=False, index=True)
    start_date         = Column(Date, nullable=True)
    end_date           = Column(Date, nullable=True)

    universe = relationship("src.infrastructure.models.universe.universe.UniverseModel",
                            back_populates="financial_assets")

    def __repr__(self) -> str:
        return (f"<UniverseFinancialAssetModel(id={self.id}, universe_id={self.universe_id}, "
                f"financial_asset_id={self.financial_asset_id})>")
