"""
Factor Serie Collection Port - Repository interface for FactorSerieCollection entities.

This port defines the contract for repositories that handle FactorSerieCollection
entities, ensuring consistent access patterns for optimization operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.factor_serie_collection import FactorSerieCollection


class FactorSerieCollectionPort(ABC):
    """Port interface for FactorSerieCollection repositories"""
    
    @abstractmethod
    def create_from_factor_list(self, factor_list: List) -> Optional[FactorSerieCollection]:
        """
        Create a FactorSerieCollection from a list of factors.
        
        Args:
            factor_list: List of Factor entities
            
        Returns:
            FactorSerieCollection entity or None if creation failed
        """
        pass
    
    @abstractmethod
    def get_factors_by_group(self, group: str) -> Optional[FactorSerieCollection]:
        """
        Get all factors in a group as a FactorSerieCollection.
        
        Args:
            group: The factor group
            
        Returns:
            FactorSerieCollection containing factors in the group or None
        """
        pass
    
    @abstractmethod
    def get_factors_by_subgroup(self, subgroup: str) -> Optional[FactorSerieCollection]:
        """
        Get all factors in a subgroup as a FactorSerieCollection.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            FactorSerieCollection containing factors in the subgroup or None
        """
        pass
    
    @abstractmethod
    def get_all_factors(self) -> Optional[FactorSerieCollection]:
        """
        Get all factors as a FactorSerieCollection.
        
        Returns:
            FactorSerieCollection containing all factors or None
        """
        pass
    
    @abstractmethod
    def filter_factors_by_criteria(self, criteria: dict) -> Optional[FactorSerieCollection]:
        """
        Filter factors by multiple criteria and return as FactorSerieCollection.
        
        Args:
            criteria: Dictionary of filter criteria (e.g., {'data_type': 'float', 'source': 'market'})
            
        Returns:
            FactorSerieCollection containing filtered factors or None
        """
        pass