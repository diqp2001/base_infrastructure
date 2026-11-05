"""
ORM model for ETFShareOption - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, ForeignKey

from src.infrastructure.models.finance.financial_assets.derivative.option.options import OptionsModel
from src.infrastructure.models.finance.financial_assets.derivative.option.share_option_terms import ShareOptionTermsMixin


class ETFShareOptionModel(ShareOptionTermsMixin, OptionsModel):
    """
    SQLAlchemy ORM model for options on ETF shares (underlying_asset_id -> etf_shares).
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'etf_share_options'

    id = Column(Integer, ForeignKey("options.id"), primary_key=True)
    # exchange_id, strike_price, multiplier, expiry: ShareOptionTermsMixin

    __mapper_args__ = {
        "polymorphic_identity": "ETFShareOption",
    }

    def __repr__(self):
        return f"<ETFShareOption(id={self.id}, symbol={self.symbol})>"
