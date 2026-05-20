"""
CompanyShareTransactionValueFactor Port - Repository interface for CompanyShareTransactionValueFactor entities.

This port defines the contract for repositories that handle CompanyShareTransactionValueFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor


class CompanyShareTransactionValueFactorPort(ABC):
    """Port interface for CompanyShareTransactionValueFactor repositories"""
    
    pass