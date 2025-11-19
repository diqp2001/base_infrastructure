"""
Country Repository - handles persistence for Country entities.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.country import Country
from src.infrastructure.models.country import Country as CountryModel
from src.infrastructure.repositories.local_repo.geographic.geographic_repository import GeographicRepository
from src.infrastructure.repositories.mappers.country_mapper import CountryMapper


class CountryRepository(GeographicRepository):
    """Repository for Country entities."""
    
    @property
    def model_class(self):
        """Return the Country ORM model class."""
        return CountryModel
    
    def _to_entity(self, model: CountryModel) -> Optional[Country]:
        """Convert ORM model to domain entity."""
        if not model:
            return None
        return CountryMapper.to_domain(model)
    
    def _to_model(self, entity: Country) -> CountryModel:
        """Convert domain entity to ORM model."""
        return CountryMapper.to_orm(entity)
    
    def get_by_iso_code(self, iso_code: str) -> Optional[Country]:
        """Get country by ISO code."""
        model = self.session.query(CountryModel).filter(
            CountryModel.iso_code == iso_code
        ).first()
        return self._to_entity(model) if model else None
    
    def get_by_continent(self, continent: str) -> List[Country]:
        """Get all countries in a continent."""
        models = self.session.query(CountryModel).filter(
            CountryModel.continent == continent
        ).all()
        return [self._to_entity(model) for model in models if model]
    
    def exists_by_iso_code(self, iso_code: str) -> bool:
        """Check if country exists by ISO code."""
        return self.session.query(CountryModel).filter(
            CountryModel.iso_code == iso_code
        ).first() is not None