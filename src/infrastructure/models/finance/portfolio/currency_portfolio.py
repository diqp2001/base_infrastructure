from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel


class CurrencyPortfolioModel(PortfolioModel):
    """
    SQLAlchemy model for CurrencyPortfolio.
    Mirrors CompanySharePortfolioModel — a portfolio holding only currency positions.
    """
    __tablename__ = 'currency_portfolios'

    id = Column(Integer, ForeignKey("portfolios.id"), primary_key=True)

    currency_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.currency_portfolio_holding.CurrencyPortfolioHoldingModel",
        back_populates="currency_portfolios",
    )
    currency_portfolio_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding.CurrencyPortfolioPortfolioHoldingModel",
        back_populates="currency_portfolio",
    )

    __mapper_args__ = {
        "polymorphic_identity": "CurrencyPortfolio",
    }
