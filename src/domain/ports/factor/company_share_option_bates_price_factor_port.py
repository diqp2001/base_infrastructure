"""
Company Share Option Bates Price Factor Port - Repository interface for CompanyShareOptionBatesPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionBatesPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_bates_price_factor import CompanyShareOptionBatesPriceFactor


class CompanyShareOptionBatesPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionBatesPriceFactor repositories"""
    pass