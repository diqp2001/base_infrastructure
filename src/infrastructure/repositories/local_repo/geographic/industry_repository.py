"""
Industry Repository - handles persistence for Industry entities.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.industry import Industry
from src.infrastructure.models.industry import Industry as IndustryModel
from src.infrastructure.repositories.local_repo.geographic.geographic_repository import GeographicRepository
from src.infrastructure.repositories.mappers.industry_mapper import IndustryMapper


class IndustryRepository(GeographicRepository):
    """Repository for Industry entities."""
    
    @property
    def model_class(self):
        """Return the Industry ORM model class."""
        return IndustryModel
    
    def _to_entity(self, model: IndustryModel) -> Optional[Industry]:
        """Convert ORM model to domain entity."""
        if not model:
            return None
        return IndustryMapper.to_domain(model)
    
    def _to_model(self, entity: Industry) -> IndustryModel:
        """Convert domain entity to ORM model."""
        return IndustryMapper.to_orm(entity)
    
    def get_by_sector(self, sector_name: str) -> List[Industry]:
        """Get industries by sector name."""
        if hasattr(IndustryModel, 'sector_name'):
            models = self.session.query(IndustryModel).filter(
                IndustryModel.sector_name == sector_name
            ).all()
            return [self._to_entity(model) for model in models if model]
        return []
    
    def get_by_classification_system(self, classification_system: str) -> List[Industry]:
        """Get industries by classification system."""
        if hasattr(IndustryModel, 'classification_system'):
            models = self.session.query(IndustryModel).filter(
                IndustryModel.classification_system == classification_system
            ).all()
            return [self._to_entity(model) for model in models if model]
        return []
    
    def get_by_name(self, name: str) -> Optional[Industry]:
        """Get industry by name."""
        model = self.session.query(IndustryModel).filter(
            IndustryModel.name == name
        ).first()
        return self._to_entity(model) if model else None
    
    def _get_next_available_industry_id(self) -> int:
        """
        Get the next available ID for industry creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(IndustryModel.id).order_by(IndustryModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available industry ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get_industry(self, name: str, sector_name: Optional[str] = None,
                               classification_system: Optional[str] = None,
                               description: Optional[str] = None) -> Optional[Industry]:
        """
        Create industry entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as BaseFactorRepository._create_or_get_factor().
        
        Args:
            name: Industry name (unique identifier)
            sector_name: Sector this industry belongs to
            classification_system: Classification system (e.g., 'GICS', 'ICB')
            description: Industry description
            
        Returns:
            Industry: Created or existing entity
        """
        # Check if entity already exists by name (unique identifier)
        existing_industry = self.get_by_name(name)
        if existing_industry:
            return existing_industry
        
        try:
            # Generate next available ID
            next_id = self._get_next_available_industry_id()
            
            # Create new industry entity
            new_industry = Industry(
                id=next_id,
                name=name,
                sector_name=sector_name,
                classification_system=classification_system,
                description=description
            )
            
            # Convert to ORM model and add to database
            industry_model = self._to_model(new_industry)
            self.session.add(industry_model)
            self.session.commit()
            
            return self._to_entity(industry_model)
            
        except Exception as e:
            self.session.rollback()
            print(f"Error creating industry {name}: {str(e)}")
            return None