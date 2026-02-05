"""
Mapper for FactorSerieCollection optimization operations.

This mapper handles conversions between FactorSerieCollection and various
data formats for optimization purposes. Since FactorSerieCollection is not
saved to database, this focuses on data transformation operations.
"""

from typing import List, Optional, Dict, Any
from src.domain.entities.factor.factor_serie_collection import FactorSerieCollection
from src.domain.entities.factor.factor import Factor


class FactorSerieCollectionMapper:
    """Mapper for FactorSerieCollection data transformations."""
    
    @staticmethod
    def from_factor_list(factors: List[Factor]) -> Optional[FactorSerieCollection]:
        """
        Create FactorSerieCollection from a list of Factor entities.
        
        Args:
            factors: List of Factor entities
            
        Returns:
            FactorSerieCollection or None if conversion failed
        """
        try:
            if not factors:
                return None
            
            return FactorSerieCollection(factors=factors)
        
        except Exception as e:
            print(f"Error converting factor list to FactorSerieCollection: {e}")
            return None
    
    @staticmethod
    def to_factor_list(collection: FactorSerieCollection) -> List[Factor]:
        """
        Extract list of Factor entities from FactorSerieCollection.
        
        Args:
            collection: FactorSerieCollection to convert
            
        Returns:
            List of Factor entities
        """
        try:
            if not collection:
                return []
            
            return collection.factors
        
        except Exception as e:
            print(f"Error converting FactorSerieCollection to factor list: {e}")
            return []
    
    @staticmethod
    def to_dict_list(collection: FactorSerieCollection) -> List[Dict[str, Any]]:
        """
        Convert FactorSerieCollection to list of dictionaries for serialization.
        
        Args:
            collection: FactorSerieCollection to convert
            
        Returns:
            List of dictionaries representing factors
        """
        try:
            if not collection:
                return []
            
            dict_list = []
            for factor in collection.factors:
                factor_dict = {
                    'id': factor.id,
                    'name': factor.name,
                    'group': factor.group,
                    'subgroup': factor.subgroup,
                    'data_type': factor.data_type,
                    'source': factor.source,
                    'definition': factor.definition
                }
                dict_list.append(factor_dict)
            
            return dict_list
        
        except Exception as e:
            print(f"Error converting FactorSerieCollection to dict list: {e}")
            return []
    
    @staticmethod
    def from_dict_list(dict_list: List[Dict[str, Any]]) -> Optional[FactorSerieCollection]:
        """
        Create FactorSerieCollection from list of dictionaries.
        
        Args:
            dict_list: List of dictionaries representing factors
            
        Returns:
            FactorSerieCollection or None if conversion failed
        """
        try:
            if not dict_list:
                return None
            
            factors = []
            for factor_dict in dict_list:
                factor = Factor(
                    name=factor_dict.get('name'),
                    group=factor_dict.get('group'),
                    subgroup=factor_dict.get('subgroup'),
                    data_type=factor_dict.get('data_type'),
                    source=factor_dict.get('source'),
                    definition=factor_dict.get('definition'),
                    factor_id=factor_dict.get('id')
                )
                factors.append(factor)
            
            return FactorSerieCollection(factors=factors)
        
        except Exception as e:
            print(f"Error converting dict list to FactorSerieCollection: {e}")
            return None
    
    @staticmethod
    def group_by_attribute(collection: FactorSerieCollection, attribute: str) -> Dict[Any, List[Factor]]:
        """
        Group factors in collection by a specific attribute.
        
        Args:
            collection: FactorSerieCollection to group
            attribute: Attribute name to group by
            
        Returns:
            Dictionary mapping attribute values to lists of factors
        """
        try:
            if not collection or not collection.factors:
                return {}
            
            groups = {}
            for factor in collection.factors:
                if hasattr(factor, attribute):
                    attr_value = getattr(factor, attribute)
                    if attr_value not in groups:
                        groups[attr_value] = []
                    groups[attr_value].append(factor)
            
            return groups
        
        except Exception as e:
            print(f"Error grouping factors by {attribute}: {e}")
            return {}
    
    @staticmethod
    def filter_by_criteria(collection: FactorSerieCollection, criteria: Dict[str, Any]) -> Optional[FactorSerieCollection]:
        """
        Filter factors in collection by criteria.
        
        Args:
            collection: FactorSerieCollection to filter
            criteria: Dictionary of attribute-value pairs for filtering
            
        Returns:
            Filtered FactorSerieCollection or None
        """
        try:
            if not collection or not collection.factors:
                return None
            
            filtered_factors = []
            for factor in collection.factors:
                match = True
                for attr, value in criteria.items():
                    if hasattr(factor, attr):
                        if getattr(factor, attr) != value:
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
            print(f"Error filtering factors by criteria: {e}")
            return None