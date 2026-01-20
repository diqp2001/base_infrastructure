"""
Continent Repository - handles persistence for Continent entities.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.continent import Continent
from src.infrastructure.models.continent import ContinentModel as ContinentModel
from src.infrastructure.repositories.local_repo.geographic.geographic_repository import GeographicRepository
from src.infrastructure.repositories.mappers.continent_mapper import ContinentMapper
from src.domain.ports.continent_port import ContinentPort


class ContinentRepository(GeographicRepository, ContinentPort):
    """Repository for Continent entities."""
    def __init__(self, session: Session):
        self.session = session
        self.data_store = []
    @property
    def model_class(self):
        """Return the Continent ORM model class."""
        return ContinentModel
    @property
    def entity_class(self):
        
        return Continent
    def _to_entity(self, model: ContinentModel) -> Optional[Continent]:
        """Convert ORM model to domain entity."""
        if not model:
            return None
        return ContinentMapper.to_domain(model)
    
    def _to_model(self, entity: Continent) -> ContinentModel:
        """Convert domain entity to ORM model."""
        return ContinentMapper.to_orm(entity)
    
    def get_by_hemisphere(self, hemisphere: str) -> List[Continent]:
        """Get continents by hemisphere."""
        if hasattr(ContinentModel, 'hemisphere'):
            models = self.session.query(ContinentModel).filter(
                ContinentModel.hemisphere == hemisphere
            ).all()
            return [self._to_entity(model) for model in models if model]
        return []
    
    def get_by_name(self, name: str) -> Optional[Continent]:
        """Get continent by name."""
        model = self.session.query(ContinentModel).filter(
            ContinentModel.name == name
        ).first()
        return self._to_entity(model) if model else None
    
    def _get_next_available_continent_id(self) -> int:
        """
        Get the next available ID for continent creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(ContinentModel.id).order_by(ContinentModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available continent ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get(self, name: str, hemisphere: Optional[str] = None,
                       description: Optional[str] = None) -> Optional[Continent]:
        """
        Create continent entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as BaseFactorRepository._create_or_get_factor().
        
        Args:
            name: Continent name (unique identifier)
            hemisphere: Hemisphere ('Northern', 'Southern')
            description: Continent description
            
        Returns:
            Continent: Created or existing entity
        """
        # Check if entity already exists by name (unique identifier)
        existing_continent = self.get_by_name(name)
        if existing_continent:
            return existing_continent
        
        try:
            # Generate next available ID
            next_id = self._get_next_available_continent_id()
            
            # Create new continent entity
            new_continent = Continent(
                id=next_id,
                name=name,
                description=description or ""  # Default to empty string
            )
            
            # Convert to ORM model and add to database
            continent_model = self._to_model(new_continent)
            self.session.add(continent_model)
            self.session.commit()
            
            return self._to_entity(continent_model)
            
        except Exception as e:
            self.session.rollback()
            print(f"Error creating continent {name}: {str(e)}")
            return None
    
    def get_or_create(self, name: str, hemisphere: str = None, description: str = None) -> Optional[Continent]:
        """
        Get or create a continent by name with dependency resolution.
        
        Args:
            name: Continent name (required)
            hemisphere: Hemisphere ('Northern', 'Southern')
            description: Continent description (optional)
            
        Returns:
            Continent entity or None if creation failed
        """
        return self._create_or_get(name, hemisphere, description)