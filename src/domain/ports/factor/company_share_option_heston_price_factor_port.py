"""
Company Share Option Heston Price Factor Port - Repository interface for CompanyShareOptionHestonPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionHestonPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor import CompanyShareOptionHestonPriceFactor


class CompanyShareOptionHestonPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionHestonPriceFactor repositories"""
    pass