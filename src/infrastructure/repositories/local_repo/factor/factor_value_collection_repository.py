"""
Factor Value Collection Repository for optimization operations.

This repository handles FactorValueCollection entities which are used for 
optimization and NOT saved to the database. It interfaces with the standard
FactorValueRepository for actual database operations.
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from src.domain.ports.factor.factor_value_collection_port import FactorValueCollectionPort
from src.domain.entities.factor.factor_value_collection import FactorValueCollection
from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.repositories.local_repo.factor.factor_value_repository import FactorValueRepository
from src.infrastructure.models.factor.factor_value import FactorValueModel


class FactorValueCollectionRepository(FactorValueCollectionPort):
    """Repository for FactorValueCollection optimization operations."""
    
    def __init__(self, session: Session, factory):
        """Initialize with database session and factory."""
        self.session = session
        self.factory = factory
        self._factor_value_repository = FactorValueRepository(session, factory)
    
    def create_from_factor_value_list(self, factor_value_list: List[FactorValue]) -> Optional[FactorValueCollection]:
        """
        Create a FactorValueCollection from a list of factor values.
        
        Args:
            factor_value_list: List of FactorValue entities
            
        Returns:
            FactorValueCollection entity or None if creation failed
        """
        try:
            if not factor_value_list:
                return None
            
            # Validate all items are FactorValue instances
            for factor_value in factor_value_list:
                if not isinstance(factor_value, FactorValue):
                    raise ValueError(f"All items must be FactorValue instances, got {type(factor_value)}")
            
            return FactorValueCollection(factor_values=factor_value_list)
        
        except Exception as e:
            print(f"Error creating FactorValueCollection from list: {e}")
            return None
    
    def bulk_save_to_database(self, collection: FactorValueCollection) -> bool:
        """
        Bulk save all factor values in the collection to the database.
        
        Args:
            collection: FactorValueCollection to save
            
        Returns:
            True if all factor values were saved successfully, False otherwise
        """
        try:
            if not collection or not collection.factor_values:
                return False
            
            success_count = 0
            
            # Prepare batch insert data
            batch_data = []
            for factor_value in collection.factor_values:
                model_data = {
                    'factor_id': factor_value.factor_id,
                    'entity_id': factor_value.entity_id,
                    'date': factor_value.date,
                    'value': factor_value.value
                }
                batch_data.append(model_data)
            
            # Use SQLAlchemy bulk insert for efficiency
            self.session.bulk_insert_mappings(FactorValueModel, batch_data)
            self.session.commit()
            
            return True
        
        except Exception as e:
            print(f"Error bulk saving FactorValueCollection: {e}")
            self.session.rollback()
            return False
    
    def get_values_by_factor_id(self, factor_id: int) -> Optional[FactorValueCollection]:
        """
        Get all factor values for a factor ID as a FactorValueCollection.
        
        Args:
            factor_id: The factor ID
            
        Returns:
            FactorValueCollection containing factor values or None
        """
        try:
            models = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id
            ).all()
            
            if not models:
                return None
            
            factor_values = [self._factor_value_repository._to_entity(model) for model in models]
            factor_values = [fv for fv in factor_values if fv is not None]
            
            if not factor_values:
                return None
            
            return FactorValueCollection(factor_values=factor_values)
        
        except Exception as e:
            print(f"Error getting factor values by factor_id {factor_id}: {e}")
            return None
    
    def get_values_by_entity_id(self, entity_id: int) -> Optional[FactorValueCollection]:
        """
        Get all factor values for an entity ID as a FactorValueCollection.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            FactorValueCollection containing factor values or None
        """
        try:
            models = self.session.query(FactorValueModel).filter(
                FactorValueModel.entity_id == entity_id
            ).all()
            
            if not models:
                return None
            
            factor_values = [self._factor_value_repository._to_entity(model) for model in models]
            factor_values = [fv for fv in factor_values if fv is not None]
            
            if not factor_values:
                return None
            
            return FactorValueCollection(factor_values=factor_values)
        
        except Exception as e:
            print(f"Error getting factor values by entity_id {entity_id}: {e}")
            return None
    
    def get_values_by_date_range(self, start_date: datetime, end_date: datetime) -> Optional[FactorValueCollection]:
        """
        Get all factor values within a date range as a FactorValueCollection.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            FactorValueCollection containing factor values in date range or None
        """
        try:
            models = self.session.query(FactorValueModel).filter(
                FactorValueModel.date >= start_date,
                FactorValueModel.date <= end_date
            ).all()
            
            if not models:
                return None
            
            factor_values = [self._factor_value_repository._to_entity(model) for model in models]
            factor_values = [fv for fv in factor_values if fv is not None]
            
            if not factor_values:
                return None
            
            return FactorValueCollection(factor_values=factor_values)
        
        except Exception as e:
            print(f"Error getting factor values by date range {start_date} to {end_date}: {e}")
            return None
    
    def get_values_by_composite_filter(self, factor_ids: List[int], entity_ids: List[int], 
                                     start_date: datetime, end_date: datetime) -> Optional[FactorValueCollection]:
        """
        Get factor values by multiple criteria as a FactorValueCollection.
        
        Args:
            factor_ids: List of factor IDs to include
            entity_ids: List of entity IDs to include
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            FactorValueCollection containing filtered factor values or None
        """
        try:
            query = self.session.query(FactorValueModel)
            
            # Apply filters
            if factor_ids:
                query = query.filter(FactorValueModel.factor_id.in_(factor_ids))
            if entity_ids:
                query = query.filter(FactorValueModel.entity_id.in_(entity_ids))
            if start_date:
                query = query.filter(FactorValueModel.date >= start_date)
            if end_date:
                query = query.filter(FactorValueModel.date <= end_date)
            
            models = query.all()
            
            if not models:
                return None
            
            factor_values = [self._factor_value_repository._to_entity(model) for model in models]
            factor_values = [fv for fv in factor_values if fv is not None]
            
            if not factor_values:
                return None
            
            return FactorValueCollection(factor_values=factor_values)
        
        except Exception as e:
            print(f"Error getting factor values by composite filter: {e}")
            return None
    
    def prepare_batch_insert(self, collection: FactorValueCollection) -> List[dict]:
        """
        Prepare factor values for efficient batch database insertion.
        
        Args:
            collection: FactorValueCollection to prepare
            
        Returns:
            List of dictionaries ready for batch insertion
        """
        try:
            if not collection or not collection.factor_values:
                return []
            
            batch_data = []
            for factor_value in collection.factor_values:
                model_data = {
                    'factor_id': factor_value.factor_id,
                    'entity_id': factor_value.entity_id,
                    'date': factor_value.date,
                    'value': factor_value.value
                }
                batch_data.append(model_data)
            
            return batch_data
        
        except Exception as e:
            print(f"Error preparing batch insert data: {e}")
            return []
    
    # Additional optimization methods
    
    def group_by_factor_id(self, collection: FactorValueCollection) -> dict:
        """
        Group factor values in collection by factor_id for optimized processing.
        
        Args:
            collection: FactorValueCollection to group
            
        Returns:
            Dictionary mapping factor_id to list of FactorValue entities
        """
        try:
            if not collection or not collection.factor_values:
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
    
    def group_by_entity_id(self, collection: FactorValueCollection) -> dict:
        """
        Group factor values in collection by entity_id for optimized processing.
        
        Args:
            collection: FactorValueCollection to group
            
        Returns:
            Dictionary mapping entity_id to list of FactorValue entities
        """
        try:
            if not collection or not collection.factor_values:
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
    
    def validate_collection_for_insert(self, collection: FactorValueCollection) -> List[str]:
        """
        Validate a collection before bulk insert operation.
        
        Args:
            collection: FactorValueCollection to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            if not collection:
                errors.append("Collection is None")
                return errors
            
            if not collection.factor_values:
                errors.append("Collection has no factor values")
                return errors
            
            for i, factor_value in enumerate(collection.factor_values):
                if not isinstance(factor_value, FactorValue):
                    errors.append(f"Item {i} is not a FactorValue instance")
                    continue
                
                if factor_value.factor_id <= 0:
                    errors.append(f"Item {i} has invalid factor_id: {factor_value.factor_id}")
                
                if factor_value.entity_id <= 0:
                    errors.append(f"Item {i} has invalid entity_id: {factor_value.entity_id}")
                
                if not factor_value.date:
                    errors.append(f"Item {i} has invalid date: {factor_value.date}")
                
                if not factor_value.value:
                    errors.append(f"Item {i} has empty value")
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return errors