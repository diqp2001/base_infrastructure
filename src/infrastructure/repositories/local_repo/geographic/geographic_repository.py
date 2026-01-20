"""
Geographic Repository - handles persistence for geographic entities.
Base repository for Country, Continent, Sector, and Industry entities.
"""

from abc import abstractmethod
from typing import Optional, List
from sqlalchemy.orm import Session

from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository


class GeographicRepository(BaseLocalRepository):
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

    def get_or_create(self, name: str, code: Optional[str] = None, **kwargs) -> Optional:
        """
        Get or create a geographic entity with dependency resolution.
        
        Args:
            name: Geographic entity name (primary identifier)
            code: Geographic entity code (optional, for countries/regions)
            **kwargs: Additional fields specific to the geographic entity type
            
        Returns:
            Domain geographic entity or None if creation failed
        """
        try:
            # First try to get existing entity by name
            existing = self.get_by_name(name)
            if existing:
                return existing
            
            # Try to get by code if provided and supported
            if code and hasattr(self.model_class, 'code'):
                existing_by_code = self.get_by_code(code)
                if existing_by_code:
                    return existing_by_code
            
            # Create new entity - implementation will vary by subclass
            # This is abstract and should be implemented by concrete classes
            return self._create_new_geographic_entity(name, code, **kwargs)
            
        except Exception as e:
            print(f"Error in get_or_create for geographic entity {name}: {e}")
            return None

    def _create_new_geographic_entity(self, name: str, code: Optional[str] = None, **kwargs) -> Optional:
        """
        Create new geographic entity - to be implemented by subclasses.
        
        Args:
            name: Geographic entity name
            code: Geographic entity code (optional)
            **kwargs: Additional fields specific to the entity type
            
        Returns:
            Created domain entity or None if failed
        """
        # This is a base implementation that subclasses can override
        # Create a generic geographic entity with minimal fields
        try:
            from datetime import datetime
            
            # Get next available ID
            next_id = self._get_next_available_id()
            
            # Create entity using the entity class
            entity_data = {
                'id': next_id,
                'name': name,
                'start_date': datetime.now().date(),
                'end_date': None
            }
            
            # Add code if supported by the model
            if code and hasattr(self.model_class, 'code'):
                entity_data['code'] = code
            
            # Add any additional kwargs
            entity_data.update(kwargs)
            
            # Create entity using entity class constructor
            new_entity = self.entity_class(**entity_data)
            
            # Add to database
            return self.add_entity(new_entity)
            
        except Exception as e:
            print(f"Error creating geographic entity {name}: {e}")
            return None