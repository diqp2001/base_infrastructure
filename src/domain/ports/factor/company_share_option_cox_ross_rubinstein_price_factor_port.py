"""
Company Share Option Cox Ross Rubinstein Price Factor Port - Repository interface for CompanyShareOptionCoxRossRubinsteinPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionCoxRossRubinsteinPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_cox_ross_rubinstein_price_factor import CompanyShareOptionCoxRossRubinsteinPriceFactor


class CompanyShareOptionCoxRossRubinsteinPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionCoxRossRubinsteinPriceFactor repositories"""
    pass