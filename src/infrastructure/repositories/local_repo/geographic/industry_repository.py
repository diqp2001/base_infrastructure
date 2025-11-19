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