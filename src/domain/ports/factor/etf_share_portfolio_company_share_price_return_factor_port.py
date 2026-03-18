"""
ETF Share Portfolio Company Share Price Return Factor Port - Repository interface for ETFSharePortfolioCompanySharePriceReturnFactor entities.

This port defines the contract for repositories that handle ETFSharePortfolioCompanySharePriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share_portfolio_company_share_price_return_factor import ETFSharePortfolioCompanySharePriceReturnFactor


class ETFSharePortfolioCompanySharePriceReturnFactorPort(ABC):
    """Port interface for ETFSharePortfolioCompanySharePriceReturnFactor repositories"""
    pass