"""
Geographic Repository - handles persistence for geographic entities.
Base repository for Country, Continent, Sector, and Industry entities.
"""

from abc import abstractmethod
from typing import Optional, List
from sqlalchemy.orm import Session

from src.infrastructure.repositories.base_repository import BaseRepository


class GeographicRepository(BaseRepository):
    """Base repository class for geographic entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    def get_by_name(self, name: str) -> Optional:
        """Get geographic entity by name."""
        entity = self.session.query(self.model_class).filter(
            self.model_class.name == name
        ).first()
        return self._to_entity(entity) if entity else None
    
    def get_by_code(self, code: str) -> Optional:
        """Get geographic entity by code (if applicable)."""
        if hasattr(self.model_class, 'code'):
            entity = self.session.query(self.model_class).filter(
                self.model_class.code == code
            ).first()
            return self._to_entity(entity) if entity else None
        return None
    
    def exists_by_name(self, name: str) -> bool:
        """Check if geographic entity exists by name."""
        return self.session.query(self.model_class).filter(
            self.model_class.name == name
        ).first() is not None
    
    def get_all_entities(self) -> List:
        """Get all geographic entities as domain entities."""
        models = self.get_all()
        return [self._to_entity(model) for model in models if model]
    
    def add_entity(self, entity) -> Optional:
        """Add a geographic entity to the database."""
        try:
            # Check if entity already exists
            if self.exists_by_name(entity.name):
                existing = self.get_by_name(entity.name)
                if existing:
                    return existing
            
            return self.create(entity)
        except Exception as e:
            print(f"Error adding {type(entity).__name__}: {str(e)}")
            return None
    
    def update_entity(self, entity_id: int, **kwargs) -> Optional:
        """Update geographic entity."""
        try:
            updated_model = self.update(entity_id, kwargs)
            return self._to_entity(updated_model) if updated_model else None
        except Exception as e:
            print(f"Error updating entity: {str(e)}")
            return None
    
    def delete_entity(self, entity_id: int) -> bool:
        """Delete geographic entity."""
        try:
            return self.delete(entity_id)
        except Exception as e:
            print(f"Error deleting entity: {str(e)}")
            return False