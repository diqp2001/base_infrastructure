"""
Country Repository - handles persistence for Country entities.
"""

import os
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.country import Country
from src.infrastructure.models.country import CountryModel as CountryModel
from src.infrastructure.repositories.local_repo.geographic.geographic_repository import GeographicRepository
from src.infrastructure.repositories.mappers.country_mapper import CountryMapper
from src.domain.ports.country_port import CountryPort


class CountryRepository(GeographicRepository, CountryPort):
    """Repository for Country entities."""
    def __init__(self, session: Session, factory):
        """Initialize CountryRepository with database session."""
        self.session = session
        self.factory = factory
        self.data_store = []
    @property
    def model_class(self):
        """Return the Country ORM model class."""
        return CountryModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Country."""
        return Country
    
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
    
    def get_by_name(self, name: str) -> Optional[Country]:
        """Get country by name."""
        model = self.session.query(CountryModel).filter(
            CountryModel.name == name
        ).first()
        return self._to_entity(model) if model else None
    
    def _get_next_available_country_id(self) -> int:
        """
        Get the next available ID for country creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(CountryModel.id).order_by(CountryModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available country ID: {str(e)}_{os.path.abspath(__file__)}")
            return 1  # Default to 1 if query fails
    
    def get_or_create(self, name: str, iso_code: Optional[str] = None,
                      continent_id: Optional[int] = None, currency: Optional[str] = None) -> Optional[Country]:
        """
        Get or create a country by name with dependency resolution.
        
        Args:
            name: Country name (required)
            iso_code: ISO country code (e.g., 'US', 'UK')
            continent_id: ID of the continent (defaults to 1)
            currency: Currency code (optional)
            
        Returns:
            Country entity or None if creation failed
        """
        return self._create_or_get(name, iso_code, continent_id, currency)
    
    def _create_or_get(self, name: str, iso_code: Optional[str] = None,
                              continent_id: Optional[int] = None, currency: Optional[str] = None) -> Optional[Country]:
        """
        Create country entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as BaseFactorRepository._create_or_get_factor().
        
        Args:
            name: Country name (unique identifier)
            iso_code: ISO country code (e.g., 'US', 'UK')
            continent_id: Continent ID (defaults to 1)
            currency: Currency code
            
        Returns:
            Country: Created or existing entity
        """
        # Check if entity already exists by name (unique identifier)
        existing_country = self.get_by_name(name)
        if existing_country:
            return existing_country
        
        # Also check by ISO code if provided
        if iso_code:
            existing_by_iso = self.get_by_iso_code(iso_code)
            if existing_by_iso:
                return existing_by_iso
        
        try:
            # Generate next available ID
            next_id = self._get_next_available_country_id()
            
            # Create new country entity
            new_country = Country(
                id=next_id,
                name=name,
                continent_id=continent_id or 1  # Use provided continent_id or default to 1
            )
            
            # Convert to ORM model and add to database
            country_model = self._to_model(new_country)
            self.session.add(country_model)
            self.session.commit()
            
            return self._to_entity(country_model)
            
        except Exception as e:
            self.session.rollback()
            print(f"Error creating country {name}: {str(e)}_{os.path.abspath(__file__)}")
            return None