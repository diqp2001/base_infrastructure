"""
Sector Repository - handles persistence for Sector entities.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.sector import Sector
from src.infrastructure.models.sector import Sector as SectorModel
from src.infrastructure.repositories.local_repo.geographic.geographic_repository import GeographicRepository
from src.infrastructure.repositories.mappers.sector_mapper import SectorMapper


class SectorRepository(GeographicRepository):
    """Repository for Sector entities."""
    
    @property
    def model_class(self):
        """Return the Sector ORM model class."""
        return SectorModel
    
    def _to_entity(self, model: SectorModel) -> Optional[Sector]:
        """Convert ORM model to domain entity."""
        if not model:
            return None
        return SectorMapper.to_domain(model)
    
    def _to_model(self, entity: Sector) -> SectorModel:
        """Convert domain entity to ORM model."""
        return SectorMapper.to_orm(entity)
    
    def get_by_classification_system(self, classification_system: str) -> List[Sector]:
        """Get sectors by classification system."""
        if hasattr(SectorModel, 'classification_system'):
            models = self.session.query(SectorModel).filter(
                SectorModel.classification_system == classification_system
            ).all()
            return [self._to_entity(model) for model in models if model]
        return []
    
    def get_by_name(self, name: str) -> Optional[Sector]:
        """Get sector by name."""
        model = self.session.query(SectorModel).filter(
            SectorModel.name == name
        ).first()
        return self._to_entity(model) if model else None
    
    def _get_next_available_sector_id(self) -> int:
        """
        Get the next available ID for sector creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(SectorModel.id).order_by(SectorModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available sector ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get(self, name: str, classification_system: Optional[str] = None,
                             description: Optional[str] = None) -> Optional[Sector]:
        """
        Create sector entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as BaseFactorRepository._create_or_get_factor().
        
        Args:
            name: Sector name (unique identifier)
            classification_system: Classification system (e.g., 'GICS', 'ICB')
            description: Sector description
            
        Returns:
            Sector: Created or existing entity
        """
        # Check if entity already exists by name (unique identifier)
        existing_sector = self.get_by_name(name)
        if existing_sector:
            return existing_sector
        
        try:
            # Generate next available ID
            next_id = self._get_next_available_sector_id()
            
            # Create new sector entity
            new_sector = Sector(
                id=next_id,
                name=name,
                description=description or ""  # Default to empty string
            )
            
            # Convert to ORM model and add to database
            sector_model = self._to_model(new_sector)
            self.session.add(sector_model)
            self.session.commit()
            
            return self._to_entity(sector_model)
            
        except Exception as e:
            self.session.rollback()
            print(f"Error creating sector {name}: {str(e)}")
            return None