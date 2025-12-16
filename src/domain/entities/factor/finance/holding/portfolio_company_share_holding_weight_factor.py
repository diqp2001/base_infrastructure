from __future__ import annotations
from typing import Optional

from .portfolio_company_share_holding_factor import PortfolioCompanyShareHoldingFactor


class PortfolioCompanyShareHoldingWeightFactor(PortfolioCompanyShareHoldingFactor):
    """
    Factor representing the weight of a company share within a PortfolioCompanyShare.

    Identification-only. The actual weight values are stored as FactorValues
    keyed by portfolio, holding, and date.
    """
    pass
