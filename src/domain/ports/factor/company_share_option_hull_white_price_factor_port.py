"""
Company Share Option Hull White Price Factor Port - Repository interface for CompanyShareOptionHullWhitePriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionHullWhitePriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_hull_white_price_factor import CompanyShareOptionHullWhitePriceFactor


class CompanyShareOptionHullWhitePriceFactorPort(ABC):
    """Port interface for CompanyShareOptionHullWhitePriceFactor repositories"""
    pass