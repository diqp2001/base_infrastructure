"""
Company Share Option Dupire Local Volatility Price Factor Port - Repository interface for CompanyShareOptionDupireLocalVolatilityPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionDupireLocalVolatilityPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_dupire_local_volatility_price_factor import CompanyShareOptionDupireLocalVolatilityPriceFactor


class CompanyShareOptionDupireLocalVolatilityPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionDupireLocalVolatilityPriceFactor repositories"""
    pass