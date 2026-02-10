"""
src/infrastructure/mappers/factor_dependency_mapper.py

Mapper class for converting between FactorDependency domain entities and infrastructure models.
Follows DDD principles by providing clear separation between domain and infrastructure concerns.
"""

from typing import Optional, List

from src.domain.entities.factor.factor_dependency import FactorDependency
from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel


class FactorDependencyMapper:
    """
    Mapper class for FactorDependency entity/model conversions.
    
    Provides bidirectional mapping between:
    - Domain entity: FactorDependency (pure business logic)  
    - Infrastructure model: FactorDependencyModel (SQLAlchemy ORM)
    """
    
    @staticmethod
    def model_to_entity(model: FactorDependencyModel) -> FactorDependency:
        """
        Convert SQLAlchemy model to domain entity.
        
        Args:
            model: FactorDependencyModel instance from database
            
        Returns:
            FactorDependency domain entity
        """
        return FactorDependency(
            id=model.id,
            dependent_factor_id=model.dependent_factor_id,
            independent_factor_id=model.independent_factor_id
        )
    
    @staticmethod
    def entity_to_model(entity: FactorDependency) -> FactorDependencyModel:
        """
        Convert domain entity to SQLAlchemy model.
        
        Args:
            entity: FactorDependency domain entity
            
        Returns:
            FactorDependencyModel for database persistence
        """
        return FactorDependencyModel(
            id=entity.id,
            dependent_factor_id=entity.dependent_factor_id,
            independent_factor_id=entity.independent_factor_id
        )
    
    @staticmethod
    def models_to_entities(models: List[FactorDependencyModel]) -> List[FactorDependency]:
        """
        Convert list of SQLAlchemy models to domain entities.
        
        Args:
            models: List of FactorDependencyModel instances
            
        Returns:
            List of FactorDependency domain entities
        """
        return [FactorDependencyMapper.model_to_entity(model) for model in models]
    
    @staticmethod
    def entities_to_models(entities: List[FactorDependency]) -> List[FactorDependencyModel]:
        """
        Convert list of domain entities to SQLAlchemy models.
        
        Args:
            entities: List of FactorDependency domain entities
            
        Returns:
            List of FactorDependencyModel instances
        """
        return [FactorDependencyMapper.entity_to_model(entity) for entity in entities]
    
    @staticmethod
    def update_model_from_entity(model: FactorDependencyModel, entity: FactorDependency) -> FactorDependencyModel:
        """
        Update existing SQLAlchemy model with values from domain entity.
        
        Args:
            model: Existing FactorDependencyModel instance
            entity: FactorDependency domain entity with updated values
            
        Returns:
            Updated FactorDependencyModel instance
        """
        model.dependent_factor_id = entity.dependent_factor_id
        model.independent_factor_id = entity.independent_factor_id
        return model