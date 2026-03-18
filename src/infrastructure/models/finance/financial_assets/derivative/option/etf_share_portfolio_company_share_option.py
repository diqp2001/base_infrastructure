from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from src.infrastructure.models.finance.financial_assets.derivative.option.options import OptionsModel
from sqlalchemy.orm import relationship

class ETFSharePortfolioCompanyShareOptionModel(OptionsModel):
    """
    SQLAlchemy ORM model for ETF Share Portfolio Company Share Options.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'etf_share_portfolio_company_share_options'

    id = Column(Integer, ForeignKey("options.id"), primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    
    # ETF share portfolio company share option specific fields
    strike_price = Column(Numeric(precision=15, scale=6), nullable=True)
    multiplier = Column(Numeric(precision=10, scale=2), nullable=True, default=1.0)
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="etf_share_portfolio_company_share_options") 
    
    __mapper_args__ = {
        "polymorphic_identity": "etf_share_portfolio_company_share_option",
    }

    def __repr__(self):
        return f"<ETFSharePortfolioCompanyShareOption(id={self.id}, symbol={self.symbol}, strike={self.strike_price})>"