"""
CompanyShareOrderQuantityFactor Port - Repository interface for CompanyShareOrderQuantityFactor entities.

This port defines the contract for repositories that handle CompanyShareOrderQuantityFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor


class CompanyShareOrderQuantityFactorPort(ABC):
    """Port interface for CompanyShareOrderQuantityFactor repositories"""
    
    pass