"""
Continent Repository - handles persistence for Continent entities.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.continent import Continent
from src.infrastructure.models.continent import Continent as ContinentModel
from src.infrastructure.repositories.local_repo.geographic.geographic_repository import GeographicRepository
from src.infrastructure.repositories.mappers.continent_mapper import ContinentMapper
from src.domain.ports.continent_port import ContinentPort


class ContinentRepository(GeographicRepository, ContinentPort):
    """Repository for Continent entities."""
    
    @property
    def model_class(self):
        """Return the Continent ORM model class."""
        return ContinentModel
    
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