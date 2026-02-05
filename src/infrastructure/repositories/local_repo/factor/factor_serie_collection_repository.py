"""
Factor Serie Collection Repository for optimization operations.

This repository handles FactorSerieCollection entities which are used for 
optimization and NOT saved to the database. It interfaces with the standard
FactorRepository for actual database operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.ports.factor.factor_serie_collection_port import FactorSerieCollectionPort
from src.domain.entities.factor.factor_serie_collection import FactorSerieCollection
from src.domain.entities.factor.factor import Factor
from src.infrastructure.repositories.local_repo.factor.factor_repository import FactorRepository


class FactorSerieCollectionRepository(FactorSerieCollectionPort):
    """Repository for FactorSerieCollection optimization operations."""
    
    def __init__(self, session: Session, factory):
        """Initialize with database session and factory."""
        self.session = session
        self.factory = factory
        self._factor_repository = FactorRepository(session, factory)
    
    def create_from_factor_list(self, factor_list: List[Factor]) -> Optional[FactorSerieCollection]:
        """
        Create a FactorSerieCollection from a list of factors.
        
        Args:
            factor_list: List of Factor entities
            
        Returns:
            FactorSerieCollection entity or None if creation failed
        """
        try:
            if not factor_list:
                return None
            
            # Validate all items are Factor instances
            for factor in factor_list:
                if not isinstance(factor, Factor):
                    raise ValueError(f"All items must be Factor instances, got {type(factor)}")
            
            return FactorSerieCollection(factors=factor_list)
        
        except Exception as e:
            print(f"Error creating FactorSerieCollection from list: {e}")
            return None
    
    def get_factors_by_group(self, group: str) -> Optional[FactorSerieCollection]:
        """
        Get all factors in a group as a FactorSerieCollection.
        
        Args:
            group: The factor group
            
        Returns:
            FactorSerieCollection containing factors in the group or None
        """
        try:
            factors = self._factor_repository.get_by_group(group)
            if not factors:
                return None
            
            return FactorSerieCollection(factors=factors)
        
        except Exception as e:
            print(f"Error getting factors by group {group}: {e}")
            return None
    
    def get_factors_by_subgroup(self, subgroup: str) -> Optional[FactorSerieCollection]:
        """
        Get all factors in a subgroup as a FactorSerieCollection.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            FactorSerieCollection containing factors in the subgroup or None
        """
        try:
            factors = self._factor_repository.get_by_subgroup(subgroup)
            if not factors:
                return None
            
            return FactorSerieCollection(factors=factors)
        
        except Exception as e:
            print(f"Error getting factors by subgroup {subgroup}: {e}")
            return None
    
    def get_all_factors(self) -> Optional[FactorSerieCollection]:
        """
        Get all factors as a FactorSerieCollection.
        
        Returns:
            FactorSerieCollection containing all factors or None
        """
        try:
            factors = self._factor_repository.get_all()
            if not factors:
                return None
            
            # Convert models to entities if needed
            factor_entities = []
            for factor in factors:
                if isinstance(factor, Factor):
                    factor_entities.append(factor)
                else:
                    # Convert model to entity if needed
                    entity = self._factor_repository._to_entity(factor)
                    if entity:
                        factor_entities.append(entity)
            
            if not factor_entities:
                return None
            
            return FactorSerieCollection(factors=factor_entities)
        
        except Exception as e:
            print(f"Error getting all factors: {e}")
            return None
    
    def filter_factors_by_criteria(self, criteria: dict) -> Optional[FactorSerieCollection]:
        """
        Filter factors by multiple criteria and return as FactorSerieCollection.
        
        Args:
            criteria: Dictionary of filter criteria (e.g., {'data_type': 'float', 'source': 'market'})
            
        Returns:
            FactorSerieCollection containing filtered factors or None
        """
        try:
            # Get all factors first
            all_factors_collection = self.get_all_factors()
            if not all_factors_collection:
                return None
            
            # Apply filters
            filtered_factors = []
            for factor in all_factors_collection.factors:
                match = True
                
                # Check each criteria
                for key, value in criteria.items():
                    if hasattr(factor, key):
                        if getattr(factor, key) != value:
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if match:
                    filtered_factors.append(factor)
            
            if not filtered_factors:
                return None
            
            return FactorSerieCollection(factors=filtered_factors)
        
        except Exception as e:
            print(f"Error filtering factors by criteria {criteria}: {e}")
            return None