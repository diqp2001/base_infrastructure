"""
Geographic Service - handles creation and management of geographic entities.
Provides a service layer for creating geographic domain entities like Country, Continent, Sector, Industry.
"""

from typing import Optional, List, Dict, Any

from src.domain.entities.country import Country
from src.domain.entities.continent import Continent
from src.domain.entities.sector import Sector
from src.domain.entities.industry import Industry


class GeographicService:
    """Service for creating and managing geographic domain entities."""
    
    def __init__(self, db_type: str = 'sqlite'):
        """Initialize the service with a database type."""
        self.db_type = db_type
    
    def create_country(
        self,
        name: str,
        iso_code: str,
        iso3_code: str = None,
        continent: str = None,
        region: str = None,
        currency: str = None,
        timezone: str = None,
        population: int = None
    ) -> Country:
        """Create a Country entity."""
        return Country(
            name=name,
            iso_code=iso_code,
            iso3_code=iso3_code,
            continent=continent,
            region=region,
            currency=currency,
            timezone=timezone,
            population=population
        )
    
    def create_continent(
        self,
        name: str,
        code: str = None,
        hemisphere: str = None,
        area_sq_km: float = None,
        population: int = None
    ) -> Continent:
        """Create a Continent entity."""
        return Continent(
            name=name,
            code=code,
            hemisphere=hemisphere,
            area_sq_km=area_sq_km,
            population=population
        )
    
    def create_sector(
        self,
        name: str,
        code: str = None,
        description: str = None,
        classification_system: str = "GICS"
    ) -> Sector:
        """Create a Sector entity."""
        return Sector(
            name=name,
            code=code,
            description=description,
            classification_system=classification_system
        )
    
    def create_industry(
        self,
        name: str,
        code: str = None,
        sector_name: str = None,
        sector_code: str = None,
        description: str = None,
        classification_system: str = "GICS"
    ) -> Industry:
        """Create an Industry entity."""
        return Industry(
            name=name,
            code=code,
            sector_name=sector_name,
            sector_code=sector_code,
            description=description,
            classification_system=classification_system
        )
    
    def create_country_from_config(self, config: Dict[str, Any]) -> Country:
        """
        Create a Country entity from a configuration dictionary.
        
        Args:
            config: Dictionary with country configuration
                Required keys: 'name', 'iso_code'
                
        Returns:
            Country entity instance
        """
        return self.create_country(
            name=config['name'],
            iso_code=config['iso_code'],
            iso3_code=config.get('iso3_code'),
            continent=config.get('continent'),
            region=config.get('region'),
            currency=config.get('currency'),
            timezone=config.get('timezone'),
            population=config.get('population')
        )
    
    def create_continent_from_config(self, config: Dict[str, Any]) -> Continent:
        """
        Create a Continent entity from a configuration dictionary.
        
        Args:
            config: Dictionary with continent configuration
                Required keys: 'name'
                
        Returns:
            Continent entity instance
        """
        return self.create_continent(
            name=config['name'],
            code=config.get('code'),
            hemisphere=config.get('hemisphere'),
            area_sq_km=config.get('area_sq_km'),
            population=config.get('population')
        )
    
    def create_sector_from_config(self, config: Dict[str, Any]) -> Sector:
        """
        Create a Sector entity from a configuration dictionary.
        
        Args:
            config: Dictionary with sector configuration
                Required keys: 'name'
                
        Returns:
            Sector entity instance
        """
        return self.create_sector(
            name=config['name'],
            code=config.get('code'),
            description=config.get('description'),
            classification_system=config.get('classification_system', 'GICS')
        )
    
    def create_industry_from_config(self, config: Dict[str, Any]) -> Industry:
        """
        Create an Industry entity from a configuration dictionary.
        
        Args:
            config: Dictionary with industry configuration
                Required keys: 'name'
                
        Returns:
            Industry entity instance
        """
        return self.create_industry(
            name=config['name'],
            code=config.get('code'),
            sector_name=config.get('sector_name'),
            sector_code=config.get('sector_code'),
            description=config.get('description'),
            classification_system=config.get('classification_system', 'GICS')
        )
    
    def create_entity_from_config(self, entity_type: str, config: Dict[str, Any]):
        """
        Create a geographic entity from configuration based on entity type.
        
        Args:
            entity_type: Type of entity ('country', 'continent', 'sector', 'industry')
            config: Configuration dictionary
            
        Returns:
            Geographic entity instance
        """
        entity_type = entity_type.lower()
        
        if entity_type == 'country':
            return self.create_country_from_config(config)
        elif entity_type == 'continent':
            return self.create_continent_from_config(config)
        elif entity_type == 'sector':
            return self.create_sector_from_config(config)
        elif entity_type == 'industry':
            return self.create_industry_from_config(config)
        else:
            raise ValueError(f"Unsupported geographic entity type: {entity_type}")
    
    def validate_country_data(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate country configuration data.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if not config.get('name'):
            errors.append("Country name is required")
        
        if not config.get('iso_code'):
            errors.append("ISO code is required")
        elif len(config['iso_code']) != 2:
            errors.append("ISO code must be 2 characters")
        
        if config.get('iso3_code') and len(config['iso3_code']) != 3:
            errors.append("ISO3 code must be 3 characters")
        
        if config.get('population') and not isinstance(config['population'], int):
            errors.append("Population must be an integer")
        
        return errors
    
    def validate_continent_data(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate continent configuration data.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if not config.get('name'):
            errors.append("Continent name is required")
        
        if config.get('hemisphere') and config['hemisphere'].lower() not in ['north', 'south', 'both']:
            errors.append("Hemisphere must be 'north', 'south', or 'both'")
        
        if config.get('area_sq_km') and not isinstance(config['area_sq_km'], (int, float)):
            errors.append("Area must be a number")
        
        if config.get('population') and not isinstance(config['population'], int):
            errors.append("Population must be an integer")
        
        return errors