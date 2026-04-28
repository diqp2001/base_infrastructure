"""
Company Share Option SABR Price Factor Port - Repository interface for CompanyShareOptionSABRPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionSABRPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_sabr_price_factor import CompanyShareOptionSABRPriceFactor


class CompanyShareOptionSABRPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionSABRPriceFactor repositories"""
    pass