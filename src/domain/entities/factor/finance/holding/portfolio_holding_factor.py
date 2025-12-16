
from __future__ import annotations
from typing import Optional

from .holding_factor import HoldingFactor


class PortfolioHoldingFactor(HoldingFactor):
    """
    Factor for holdings inside a portfolio.

    Identification-only. Values like weights, returns, exposure live elsewhere.
    """
    pass
