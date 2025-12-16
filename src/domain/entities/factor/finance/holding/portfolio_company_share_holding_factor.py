from __future__ import annotations
from typing import Optional

from .portfolio_holding_factor import PortfolioHoldingFactor


class PortfolioCompanyShareHoldingFactor(PortfolioHoldingFactor):
    """
    Factor for holdings of company shares inside a PortfolioCompanyShare.

    Identification-only. Metrics like weight, price, contribution, etc.,
    are handled as FactorValues.
    """
    pass
