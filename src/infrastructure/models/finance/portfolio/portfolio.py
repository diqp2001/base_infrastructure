"""
Unified ORM model for Portfolio - combining live, mock, and snapshot portfolio data.
"""

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_entity import FinancialEntityModel


class PortfolioModel(FinancialEntityModel):
    """
    Joined-table child of FinancialEntityModel.

    portfolio_type is kept as an informational column for backward-compatible queries
    but is NO LONGER the SQLAlchemy polymorphic discriminator (entity_type on
    financial_entities is the single discriminator for the full hierarchy).
    New inserts auto-populate portfolio_type via __init__ to keep existing code working.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, ForeignKey('financial_entities.id'), primary_key=True)
    # Informational copy of the polymorphic identity — no longer the ORM discriminator.
    portfolio_type = Column(String(50), nullable=True)
    name = Column(String(200), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    positions = relationship("src.infrastructure.models.finance.position.PositionModel", back_populates="portfolios", cascade="all, delete-orphan")
    portfolio_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_holding.PortfolioHoldingsModel", back_populates="portfolios")
    security_holdings = relationship("src.infrastructure.models.finance.holding.security_holding.SecurityHoldingModel", back_populates="portfolios")
    securities = relationship(
        "src.infrastructure.models.finance.financial_assets.security.SecurityModel",
        foreign_keys="[src.infrastructure.models.finance.financial_assets.security.SecurityModel.portfolio_id]",
        back_populates="portfolios",
    )

    __mapper_args__ = {
        "polymorphic_identity": "Portfolio",
        "inherit_condition": id == FinancialEntityModel.id,
    }

    def __init__(self, **kwargs):
        if 'portfolio_type' not in kwargs:
            from sqlalchemy import inspect as sa_inspect
            try:
                poly_id = sa_inspect(type(self)).polymorphic_identity
            except Exception:
                poly_id = None
            kwargs['portfolio_type'] = poly_id or 'Portfolio'
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Portfolio(id={self.id}, name={self.name})>"
