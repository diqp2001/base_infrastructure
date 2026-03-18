"""
ETF Share Portfolio Company Share Factor Port - Repository interface for ETFSharePortfolioCompanyShareFactor entities.

This port defines the contract for repositories that handle ETFSharePortfolioCompanyShareFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share_portfolio_company_share_factor import ETFSharePortfolioCompanyShareFactor


class ETFSharePortfolioCompanyShareFactorPort(ABC):
    """Port interface for ETFSharePortfolioCompanyShareFactor repositories"""
    pass