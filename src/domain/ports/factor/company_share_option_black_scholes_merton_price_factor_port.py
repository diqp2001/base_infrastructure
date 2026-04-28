"""
Company Share Option Black Scholes Merton Price Factor Port - Repository interface for CompanyShareOptionBlackScholesMertonPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionBlackScholesMertonPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import CompanyShareOptionBlackScholesMertonPriceFactor


class CompanyShareOptionBlackScholesMertonPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionBlackScholesMertonPriceFactor repositories"""
    pass