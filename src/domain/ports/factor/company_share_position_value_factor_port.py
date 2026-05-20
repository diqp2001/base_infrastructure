"""
CompanySharePositionValueFactor Port - Repository interface for CompanySharePositionValueFactor entities.

This port defines the contract for repositories that handle CompanySharePositionValueFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor


class CompanySharePositionValueFactorPort(ABC):
    """Port interface for CompanySharePositionValueFactor repositories"""
    
    pass