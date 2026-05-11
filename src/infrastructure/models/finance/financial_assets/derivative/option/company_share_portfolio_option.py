from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from src.infrastructure.models.finance.financial_assets.derivative.option.options import OptionsModel
from sqlalchemy.orm import relationship

class CompanySharePortfolioOptionModel(OptionsModel):
    """
    SQLAlchemy ORM model for Index Future Options.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'company_share_portfolio_options'

    id = Column(Integer, ForeignKey("options.id"), primary_key=True)
    
    # Index future option specific fields
    strike_price = Column(Numeric(precision=15, scale=6), nullable=True)
    multiplier = Column(Numeric(precision=10, scale=2), nullable=True, default=1.0)
    
    # Relationships
    company_share_portfolio_option_portfolio_holdings = relationship(
        "src.infrastructure.models.finance.holding.company_share_portfolio_option_portfolio_holding.CompanySharePortfolioOptionPortfolioHoldingModel",
        back_populates="company_share_portfolio_options"
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "company_share_portfolio_options",
    }

    def __repr__(self):
        return f"<CompanySharePortfolioOption(id={self.id}, symbol={self.symbol}, strike={self.strike_price})>"