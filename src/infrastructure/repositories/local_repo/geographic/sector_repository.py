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