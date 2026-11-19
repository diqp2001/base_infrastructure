"""
src/infrastructure/models/universe/universe.py

SQLAlchemy ORM models of the universe hierarchy (joined-table inheritance, discriminator ``universe_type``):

    universes               UniverseModel            every universe: name, description, type, version, timestamps
    investment_universes    InvestmentUniverseModel  child type: id = universes.id, entity_type, currency_id

The constituents are separate tables: universe_financial_assets / universe_factors (any universe) and
universe_constituents (an investment universe's dated / weighted history).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class UniverseModel(Base):
    __tablename__ = "universes"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_universes_name_version"),)

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String(255), nullable=False, index=True)
    description   = Column(Text, nullable=True)
    universe_type = Column(String(100), nullable=False, default="Universe", index=True)
    version       = Column(Integer, nullable=False, default=1)
    created_at    = Column(DateTime, nullable=True)
    updated_at    = Column(DateTime, nullable=True)

    financial_assets = relationship(
        "src.infrastructure.models.universe.universe_financial_asset.UniverseFinancialAssetModel",
        back_populates="universe", cascade="all, delete-orphan",
        order_by="src.infrastructure.models.universe.universe_financial_asset.UniverseFinancialAssetModel.id",
    )
    factors = relationship(
        "src.infrastructure.models.universe.universe_factor.UniverseFactorModel",
        back_populates="universe", cascade="all, delete-orphan",
        order_by="src.infrastructure.models.universe.universe_factor.UniverseFactorModel.id",
    )

    __mapper_args__ = {
        "polymorphic_on": universe_type,
        "polymorphic_identity": "Universe",
    }

    def __repr__(self) -> str:
        return f"<UniverseModel(id={self.id}, name={self.name}, type={self.universe_type})>"


class InvestmentUniverseModel(UniverseModel):
    __tablename__ = "investment_universes"

    id          = Column(Integer, ForeignKey("universes.id"), primary_key=True)
    entity_type = Column(String(100), nullable=True)
    currency_id = Column(Integer, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "InvestmentUniverse",
    }

    def __repr__(self) -> str:
        return f"<InvestmentUniverseModel(id={self.id}, name={self.name})>"
