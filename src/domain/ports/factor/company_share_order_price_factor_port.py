"""
CompanyShareOrderPriceFactor Port - Repository interface for CompanyShareOrderPriceFactor entities.

This port defines the contract for repositories that handle CompanyShareOrderPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor


class CompanyShareOrderPriceFactorPort(ABC):
    """Port interface for CompanyShareOrderPriceFactor repositories"""
    
    pass