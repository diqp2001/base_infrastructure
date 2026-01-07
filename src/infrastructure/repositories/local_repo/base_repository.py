# src/infrastructure/repositories/base_repository.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.orm import Session

# Domain Entity and ORM Model Type Variables
EntityType = TypeVar("EntityType")
ModelType = TypeVar("ModelType")

class BaseLocalRepository(ABC, Generic[EntityType, ModelType]):
    """
    Base class for all repositories.
    Provides shared logic for CRUD operations and entity/model conversions.
    """
    
    def __init__(self, session: Session):
        self.session = session

    # --- CRUD Core Methods (Optionally Overridden) ---

    def add(self, model: ModelType) -> ModelType:
        """Add a new ORM model instance to the database."""
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model

    def get(self, model_id: int) -> Optional[ModelType]:
        """Retrieve ORM model by ID."""
        return self.session.get(self.model_class, model_id)

    def update(self, model_id: int, updates: dict) -> Optional[ModelType]:
        """Update model with new data."""
        model = self.session.get(self.model_class, model_id)
        if not model:
            return None
        
        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        self.session.commit()
        self.session.refresh(model)
        return model

    def delete(self, model_id: int) -> bool:
        """Delete model by ID."""
        model = self.session.get(self.model_class, model_id)
        if not model:
            return False
        self.session.delete(model)
        self.session.commit()
        return True

    def get_all(self) -> List[ModelType]:
        """Get all models of this type."""
        return self.session.query(self.model_class).all()

    def _get_next_available_id(self) -> int:
        """
        Get the next available ID for entity creation.
        Uses database auto-increment to ensure chronological ordering.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(
                self.model_class.id
            ).order_by(self.model_class.id.desc()).first()

            if max_id_result:
                return max_id_result.id + 1
            else:
                return 1  # Start from 1 if no records exist

        except Exception as e:
            print(f"Warning: Could not determine next available ID for {self.model_class.__name__}: {str(e)}")
            return 1  # Default to 1 if query fails

    # --- Abstract Methods to Implement in Child Repositories ---

    @property
    @abstractmethod
    def model_class(self):
        """Return the SQLAlchemy model class used by this repository."""
        pass

    @abstractmethod
    def _to_entity(self, infra_obj: ModelType) -> EntityType:
        """
        Convert ORM model → Domain entity.
        Must be implemented in child repositories.
        """
        pass

    # --- Standard Domain Entity CRUD Interface ---

    def create(self, entity: EntityType) -> EntityType:
        """Create new entity in database"""
        # If entity doesn't have an ID, assign the next available one
        if not hasattr(entity, 'id') or entity.id is None:
            entity.id = self._get_next_available_id()
        
        # Convert domain entity to ORM model
        model = self._to_model(entity)
        
        # Save to database
        saved_model = self.add(model)
        
        # Convert back to domain entity
        return self._to_entity(saved_model)

    @abstractmethod
    def _to_model(self, entity: EntityType) -> ModelType:
        """
        Convert Domain entity → ORM model.
        Must be implemented in child repositories.
        """
        pass
    @abstractmethod
    def _create_or_get(self):
        """
        Create entity if it doesn't exist with related entities, otherwise return existing based on name AND discriminator.
        """
        pass