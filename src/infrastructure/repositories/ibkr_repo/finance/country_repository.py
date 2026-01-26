"""
IBKR Country Repository - Interactive Brokers implementation for Countries.

This repository handles country data for IBKR financial entities, applying IBKR-specific 
business rules and handling continent dependencies.
"""

import os
from typing import Optional, List

from src.domain.entities.country import Country
from src.domain.entities.continent import Continent
from src.domain.ports.country_port import CountryPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.mappers.country_mapper import CountryMapper


class IBKRCountryRepository(BaseIBKRRepository, CountryPort):
    """
    IBKR implementation of CountryPort for country data with continent dependency management.
    """

    def __init__(self, ibkr_client, factory, mapper: CountryMapper = None):
        """
        Initialize IBKR Country Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (required)
            mapper: Country mapper for entity/model conversion (optional, will create if not provided)
        """
        self.factory = factory
        if factory:
            self.local_repo = self.factory.country_local_repo
        else:
            raise ValueError("Factory is required for IBKRCountryRepository")
        self.mapper = mapper or CountryMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for Country."""
        return Country

    def get_or_create(self, name: str) -> Optional[Country]:
        """
        Get or create a country by name with continent dependency resolution.
        
        Args:
            name: Country name (e.g., 'United States', 'Germany')
            
        Returns:
            Country entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_name(name)
            if existing:
                return existing
            
            # 2. Create new country with continent dependency
            continent = self._get_or_create_continent(self._get_continent_for_country(name))
            if not continent:
                return None
            
            # 3. Use local repository to create the country
            iso_code = self._get_iso_code_for_country(name)
            return self.local_repo.get_or_create(
                name=name,
                iso_code=iso_code,
                continent_id=continent.id
            )
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for country {name}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_by_name(self, name: str) -> Optional[Country]:
        """Get country by name (delegates to local repository)."""
        return self.local_repo.get_by_name(name)

    def get_by_id(self, entity_id: int) -> Optional[Country]:
        """Get country by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Country]:
        """Get all countries (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Country) -> Optional[Country]:
        """Add country entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Country) -> Optional[Country]:
        """Update country entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete country entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _get_or_create_continent(self, name: str) -> Optional[Continent]:
        """
        Get or create a continent using factory or continent repository if available.
        Falls back to direct continent creation if no dependencies are provided.
        
        Args:
            name: continent name (e.g., 'North America', 'Europe')
            
        Returns:
            continent domain entity
        """
        try:
            # Try factory's continent repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'continent_ibkr_repo'):
                continent_repo = self.factory.continent_ibkr_repo
                if continent_repo:
                    continent = continent_repo.get_or_create(name)
                    if continent:
                        return continent
            
            # Fallback: create minimal continent entity for basic functionality
            return Continent(
                id=None,  # Let database generate
                name=name
            )
            
        except Exception as e:
            print(f"Error getting or creating continent {name}: {e}_{os.path.abspath(__file__)}")
            # Return minimal continent as last resort
            return Continent(
                id=None,
                name=name
            )

    def _get_continent_for_country(self, country_name: str) -> str:
        """Map country name to continent name."""
        country_continent_map = {
            'United States': 'North America',
            'Canada': 'North America',
            'Mexico': 'North America',
            'Germany': 'Europe',
            'United Kingdom': 'Europe',
            'Switzerland': 'Europe',
            'Sweden': 'Europe',
            'Norway': 'Europe',
            'Denmark': 'Europe',
            'Poland': 'Europe',
            'Czech Republic': 'Europe',
            'Hungary': 'Europe',
            'Russia': 'Europe',
            'Turkey': 'Europe',
            'Japan': 'Asia',
            'China': 'Asia',
            'Hong Kong': 'Asia',
            'Singapore': 'Asia',
            'India': 'Asia',
            'South Korea': 'Asia',
            'Australia': 'Oceania',
            'New Zealand': 'Oceania',
            'South Africa': 'Africa',
            'Brazil': 'South America'
        }
        return country_continent_map.get(country_name, 'North America')  # Default to North America
    
    def _get_iso_code_for_country(self, country_name: str) -> str:
        """Map country name to ISO code."""
        country_iso_map = {
            'United States': 'US',
            'Germany': 'DE',
            'United Kingdom': 'GB',
            'Japan': 'JP',
            'Australia': 'AU',
            'Canada': 'CA',
            'Switzerland': 'CH',
            'New Zealand': 'NZ',
            'Sweden': 'SE',
            'Norway': 'NO',
            'Denmark': 'DK',
            'Poland': 'PL',
            'Czech Republic': 'CZ',
            'Hungary': 'HU',
            'Russia': 'RU',
            'China': 'CN',
            'Hong Kong': 'HK',
            'Singapore': 'SG',
            'South Africa': 'ZA',
            'Mexico': 'MX',
            'Brazil': 'BR',
            'India': 'IN',
            'South Korea': 'KR',
            'Turkey': 'TR'
        }
        return country_iso_map.get(country_name, 'US')  # Default to US