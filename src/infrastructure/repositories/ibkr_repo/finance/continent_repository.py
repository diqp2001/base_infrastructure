"""
IBKR Continent Repository - Interactive Brokers implementation for Continents.

This repository handles continent data for IBKR financial entities, serving as the 
top-level geographic entity in the dependency chain.
"""

import os
from typing import Optional, List

from src.infrastructure.repositories.mappers.continent_mapper import ContinentMapper
from src.domain.entities.continent import Continent
from src.domain.ports.continent_port import ContinentPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository


class IBKRContinentRepository(BaseIBKRRepository, ContinentPort):
    """
    IBKR implementation of ContinentPort for continent data.
    """

    def __init__(self, ibkr_client,
                    factory):
        """
        Initialize IBKR Continent Repository.
        
        Args:
            factory: Repository factory for dependency injection (required)
        """
        self.mapper = ContinentMapper()
        self.factory = factory
        if factory:
            self.local_repo = self.factory.continent_local_repo
        else:
            raise ValueError("Factory is required for IBKRContinentRepository")

    @property
    def entity_class(self):
        """Return the domain entity class for Continent."""
        return self.mapper.entity_class
    @property
    def entity_class(self):
        """Return the model entity class for Continent."""
        return self.mapper.model_class

    def _create_or_get(self, name: str) -> Optional[Continent]:
        """
        Get or create a continent by name.
        
        Args:
            name: Continent name (e.g., 'North America', 'Europe', 'Asia')
            
        Returns:
            Continent entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_name(name)
            if existing:
                return existing
            
            # 2. Use local repository to create the continent
            hemisphere = self._get_hemisphere_for_continent(name)
            description = self._get_description_for_continent(name)
            
            return self.local_repo.get_or_create(
                name=name,
                hemisphere=hemisphere,
                description=description
            )
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for continent {name}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_by_name(self, name: str) -> Optional[Continent]:
        """Get continent by name (delegates to local repository)."""
        return self.local_repo.get_by_name(name)

    def get_by_id(self, entity_id: int) -> Optional[Continent]:
        """Get continent by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Continent]:
        """Get all continents (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Continent) -> Optional[Continent]:
        """Add continent entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Continent) -> Optional[Continent]:
        """Update continent entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete continent entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _get_hemisphere_for_continent(self, continent_name: str) -> str:
        """Map continent name to hemisphere."""
        continent_hemisphere_map = {
            'North America': 'Northern',
            'South America': 'Southern',
            'Europe': 'Northern',
            'Asia': 'Northern',
            'Africa': 'Both',  # Africa spans both hemispheres
            'Australia': 'Southern',
            'Oceania': 'Southern',
            'Antarctica': 'Southern'
        }
        return continent_hemisphere_map.get(continent_name, 'Northern')  # Default to Northern
    
    def _get_description_for_continent(self, continent_name: str) -> str:
        """Get description for continent."""
        continent_descriptions = {
            'North America': 'Continent comprising Canada, United States, and Mexico',
            'South America': 'Southern continent of the Americas',
            'Europe': 'Western peninsula of Eurasia',
            'Asia': 'Largest continent by area and population',
            'Africa': 'Second-largest continent by area and population', 
            'Australia': 'Smallest continent, also known as Oceania',
            'Oceania': 'Region including Australia and Pacific islands',
            'Antarctica': 'Southernmost continent'
        }
        return continent_descriptions.get(continent_name, f'Continent: {continent_name}')