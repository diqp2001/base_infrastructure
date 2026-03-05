"""
ORM model for Index Future Options - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from src.infrastructure.models.finance.financial_assets.derivative.options import OptionsModel
from sqlalchemy.orm import relationship

class IndexFutureOptionModel(OptionsModel):
    """
    SQLAlchemy ORM model for Index Future Options.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'index_future_options'

    id = Column(Integer, ForeignKey("options.id"), primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    
    # Index future option specific fields
    strike_price = Column(Numeric(precision=15, scale=6), nullable=True)
    multiplier = Column(Numeric(precision=10, scale=2), nullable=True, default=1.0)
    index_symbol = Column(String(50), nullable=True)
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="index_future_options") 
    
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option",
    }

    def __repr__(self):
        return f"<IndexFutureOption(id={self.id}, symbol={self.symbol}, strike={self.strike_price})>"