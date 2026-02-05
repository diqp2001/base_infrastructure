"""
Mapper for FactorValueCollection optimization operations.

This mapper handles conversions between FactorValueCollection and various
data formats for batch processing and optimization purposes. Since 
FactorValueCollection is not saved to database, this focuses on data 
transformation and preparation operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from src.domain.entities.factor.factor_value_collection import FactorValueCollection
from src.domain.entities.factor.factor_value import FactorValue


class FactorValueCollectionMapper:
    """Mapper for FactorValueCollection data transformations."""
    
    @staticmethod
    def from_factor_value_list(factor_values: List[FactorValue]) -> Optional[FactorValueCollection]:
        """
        Create FactorValueCollection from a list of FactorValue entities.
        
        Args:
            factor_values: List of FactorValue entities
            
        Returns:
            FactorValueCollection or None if conversion failed
        """
        try:
            if not factor_values:
                return None
            
            return FactorValueCollection(factor_values=factor_values)
        
        except Exception as e:
            print(f"Error converting factor value list to FactorValueCollection: {e}")
            return None
    
    @staticmethod
    def to_factor_value_list(collection: FactorValueCollection) -> List[FactorValue]:
        """
        Extract list of FactorValue entities from FactorValueCollection.
        
        Args:
            collection: FactorValueCollection to convert
            
        Returns:
            List of FactorValue entities
        """
        try:
            if not collection:
                return []
            
            return collection.factor_values
        
        except Exception as e:
            print(f"Error converting FactorValueCollection to factor value list: {e}")
            return []
    
    @staticmethod
    def to_dict_list(collection: FactorValueCollection) -> List[Dict[str, Any]]:
        """
        Convert FactorValueCollection to list of dictionaries for serialization.
        
        Args:
            collection: FactorValueCollection to convert
            
        Returns:
            List of dictionaries representing factor values
        """
        try:
            if not collection:
                return []
            
            dict_list = []
            for factor_value in collection.factor_values:
                factor_value_dict = {
                    'id': factor_value.id,
                    'factor_id': factor_value.factor_id,
                    'entity_id': factor_value.entity_id,
                    'date': factor_value.date.isoformat() if factor_value.date else None,
                    'value': factor_value.value
                }
                dict_list.append(factor_value_dict)
            
            return dict_list
        
        except Exception as e:
            print(f"Error converting FactorValueCollection to dict list: {e}")
            return []
    
    @staticmethod
    def from_dict_list(dict_list: List[Dict[str, Any]]) -> Optional[FactorValueCollection]:
        """
        Create FactorValueCollection from list of dictionaries.
        
        Args:
            dict_list: List of dictionaries representing factor values
            
        Returns:
            FactorValueCollection or None if conversion failed
        """
        try:
            if not dict_list:
                return None
            
            factor_values = []
            for factor_value_dict in dict_list:
                # Convert date string back to datetime if needed
                date_value = factor_value_dict.get('date')
                if isinstance(date_value, str):
                    date_value = datetime.fromisoformat(date_value)
                
                factor_value = FactorValue(
                    id=factor_value_dict.get('id'),
                    factor_id=factor_value_dict.get('factor_id'),
                    entity_id=factor_value_dict.get('entity_id'),
                    date=date_value,
                    value=factor_value_dict.get('value')
                )
                factor_values.append(factor_value)
            
            return FactorValueCollection(factor_values=factor_values)
        
        except Exception as e:
            print(f"Error converting dict list to FactorValueCollection: {e}")
            return None
    
    @staticmethod
    def to_bulk_insert_format(collection: FactorValueCollection) -> List[Dict[str, Any]]:
        """
        Convert FactorValueCollection to format optimized for bulk database insertion.
        
        Args:
            collection: FactorValueCollection to convert
            
        Returns:
            List of dictionaries ready for SQLAlchemy bulk_insert_mappings
        """
        try:
            if not collection:
                return []
            
            bulk_data = []
            for factor_value in collection.factor_values:
                # Prepare data for direct database insertion
                insert_data = {
                    'factor_id': factor_value.factor_id,
                    'entity_id': factor_value.entity_id,
                    'date': factor_value.date,
                    'value': factor_value.value
                }
                # Don't include id for bulk insert - let database generate it
                bulk_data.append(insert_data)
            
            return bulk_data
        
        except Exception as e:
            print(f"Error converting to bulk insert format: {e}")
            return []
    
    @staticmethod
    def group_by_factor_id(collection: FactorValueCollection) -> Dict[int, List[FactorValue]]:
        """
        Group factor values by factor_id for batch processing.
        
        Args:
            collection: FactorValueCollection to group
            
        Returns:
            Dictionary mapping factor_id to lists of FactorValue entities
        """
        try:
            if not collection:
                return {}
            
            groups = {}
            for factor_value in collection.factor_values:
                factor_id = factor_value.factor_id
                if factor_id not in groups:
                    groups[factor_id] = []
                groups[factor_id].append(factor_value)
            
            return groups
        
        except Exception as e:
            print(f"Error grouping by factor_id: {e}")
            return {}
    
    @staticmethod
    def group_by_entity_id(collection: FactorValueCollection) -> Dict[int, List[FactorValue]]:
        """
        Group factor values by entity_id for batch processing.
        
        Args:
            collection: FactorValueCollection to group
            
        Returns:
            Dictionary mapping entity_id to lists of FactorValue entities
        """
        try:
            if not collection:
                return {}
            
            groups = {}
            for factor_value in collection.factor_values:
                entity_id = factor_value.entity_id
                if entity_id not in groups:
                    groups[entity_id] = []
                groups[entity_id].append(factor_value)
            
            return groups
        
        except Exception as e:
            print(f"Error grouping by entity_id: {e}")
            return {}
    
    @staticmethod
    def filter_by_criteria(collection: FactorValueCollection, criteria: Dict[str, Any]) -> Optional[FactorValueCollection]:
        """
        Filter factor values in collection by criteria.
        
        Args:
            collection: FactorValueCollection to filter
            criteria: Dictionary of attribute-value pairs for filtering
            
        Returns:
            Filtered FactorValueCollection or None
        """
        try:
            if not collection:
                return None
            
            filtered_values = []
            for factor_value in collection.factor_values:
                match = True
                for attr, value in criteria.items():
                    if hasattr(factor_value, attr):
                        factor_attr_value = getattr(factor_value, attr)
                        
                        # Special handling for date comparisons
                        if attr == 'date' and isinstance(value, datetime):
                            if factor_attr_value.date() != value.date():
                                match = False
                                break
                        elif factor_attr_value != value:
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if match:
                    filtered_values.append(factor_value)
            
            if not filtered_values:
                return None
            
            return FactorValueCollection(factor_values=filtered_values)
        
        except Exception as e:
            print(f"Error filtering factor values by criteria: {e}")
            return None
    
    @staticmethod
    def merge_collections(collections: List[FactorValueCollection]) -> Optional[FactorValueCollection]:
        """
        Merge multiple FactorValueCollection entities into one.
        
        Args:
            collections: List of FactorValueCollection entities to merge
            
        Returns:
            Merged FactorValueCollection or None if merge failed
        """
        try:
            if not collections:
                return None
            
            all_factor_values = []
            for collection in collections:
                if collection and collection.factor_values:
                    all_factor_values.extend(collection.factor_values)
            
            if not all_factor_values:
                return None
            
            return FactorValueCollection(factor_values=all_factor_values)
        
        except Exception as e:
            print(f"Error merging FactorValueCollection entities: {e}")
            return None
    
    @staticmethod
    def split_by_batch_size(collection: FactorValueCollection, batch_size: int) -> List[FactorValueCollection]:
        """
        Split a large FactorValueCollection into smaller batches.
        
        Args:
            collection: FactorValueCollection to split
            batch_size: Maximum number of factor values per batch
            
        Returns:
            List of FactorValueCollection entities (batches)
        """
        try:
            if not collection or not collection.factor_values or batch_size <= 0:
                return []
            
            batches = []
            factor_values = collection.factor_values
            
            for i in range(0, len(factor_values), batch_size):
                batch_values = factor_values[i:i + batch_size]
                batch_collection = FactorValueCollection(factor_values=batch_values)
                batches.append(batch_collection)
            
            return batches
        
        except Exception as e:
            print(f"Error splitting FactorValueCollection into batches: {e}")
            return []