"""
ORM model for Derivatives - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class DerivativeModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Derivative securities.
    Base class for all derivative instruments.
    """
    __tablename__ = 'derivatives'

    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    # FK to financial_entities so the underlying can be any FinancialEntity
    # (FinancialAsset or Portfolio), not just a financial asset.
    underlying_asset_id = Column(Integer, ForeignKey('financial_entities.id'), nullable=False)
    underlying_asset = relationship(
        "src.infrastructure.models.finance.financial_entity.FinancialEntityModel",
        foreign_keys=[underlying_asset_id],
        back_populates="underlying_derivatives"
    )
    currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel",foreign_keys=[currency_id], back_populates="derivatives")
    
    # ONE derivative → MANY derivative_portfolio_holdings
    derivative_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.derivative.derivative_portfolio_holding.DerivativePortfolioHoldingModel",
        back_populates="derivatives"
    )
    
    __mapper_args__ = {
    "polymorphic_identity": "derivatives",
    "inherit_condition": id == FinancialAssetModel.id,  # 🔥 REQUIRED
}

    def __repr__(self):
        return f"<Derivative(id={self.id})>"