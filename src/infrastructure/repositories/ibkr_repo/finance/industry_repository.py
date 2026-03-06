"""
IBKR Industry Repository - Interactive Brokers implementation for Industries.

This repository handles industry data for IBKR financial entities, applying IBKR-specific 
business rules and handling sector dependencies.
"""

import os
from typing import Optional, List

from src.domain.entities.industry import Industry
from src.domain.entities.sector import Sector
from src.domain.ports.industry_port import IndustryPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.mappers.industry_mapper import IndustryMapper


class IBKRIndustryRepository(BaseIBKRRepository, IndustryPort):
    """
    IBKR implementation of IndustryPort for industry data with sector dependency management.
    """

    def __init__(self, ibkr_client, factory, mapper: IndustryMapper = None):
        """
        Initialize IBKR Industry Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (required)
            mapper: Industry mapper for entity/model conversion (optional, will create if not provided)
        """
        self.factory = factory
        if factory:
            self.local_repo = self.factory.industry_local_repo
        else:
            raise ValueError("Factory is required for IBKRIndustryRepository")
        self.mapper = mapper or IndustryMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for Industry."""
        return Industry

    @property
    def model_class(self):
        """Return the model entity class for Industry."""
        return self.mapper.model_class

    def _create_or_get(self, name: str) -> Optional[Industry]:
        """
        Get or create an industry by name with sector dependency resolution.
        
        Args:
            name: Industry name (e.g., 'Technology Hardware & Equipment', 'Software')
            
        Returns:
            Industry entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_name(name)
            if existing:
                return existing
            
            # 2. Create new industry with sector dependency
            sector = self._get_or_create_sector(self._get_sector_for_industry(name))
            if not sector:
                return None
            
            # 3. Use local repository to create the industry
            return self.local_repo.get_or_create(
                name=name,
                sector_name=sector.name,
                description=f"{name} industry within {sector.name} sector"
            )
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for industry {name}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_by_name(self, name: str) -> Optional[Industry]:
        """Get industry by name (delegates to local repository)."""
        return self.local_repo.get_by_name(name)

    def get_by_id(self, entity_id: int) -> Optional[Industry]:
        """Get industry by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Industry]:
        """Get all industries (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Industry) -> Optional[Industry]:
        """Add industry entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Industry) -> Optional[Industry]:
        """Update industry entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete industry entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def get_by_sector(self, sector_name: str) -> List[Industry]:
        """Get industries by sector name (delegates to local repository)."""
        return self.local_repo.get_by_sector(sector_name)

    def get_by_classification_system(self, classification_system: str) -> List[Industry]:
        """Get industries by classification system (delegates to local repository)."""
        return self.local_repo.get_by_classification_system(classification_system)

    def _get_or_create_sector(self, name: str) -> Optional[Sector]:
        """
        Get or create a sector using factory or sector repository if available.
        Falls back to direct sector creation if no dependencies are provided.
        
        Args:
            name: sector name (e.g., 'Technology', 'Healthcare')
            
        Returns:
            sector domain entity
        """
        try:
            # Try factory's sector repository first (preferred approach)
            if self.factory and hasattr(self.factory, 'sector_ibkr_repo'):
                sector_repo = self.factory.sector_ibkr_repo
                if sector_repo:
                    sector = sector_repo._create_or_get(name)
                    if sector:
                        return sector
            
            # Fallback: use local sector repository directly
            if self.factory and hasattr(self.factory, 'sector_local_repo'):
                sector_local_repo = self.factory.sector_local_repo
                return sector_local_repo.get_or_create(
                    name=name,
                    description=f"{name} sector"
                )
            
        except Exception as e:
            print(f"Error getting or creating sector {name}: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_sector_for_industry(self, industry_name: str) -> str:
        """Map industry name to sector name based on IBKR industry classifications."""
        industry_sector_map = {
            # Technology sector
            'Technology Hardware & Equipment': 'Technology',
            'Software': 'Technology',
            'Semiconductors & Semiconductor Equipment': 'Technology',
            'IT Services': 'Technology',
            'Electronic Equipment & Components': 'Technology',
            
            # Healthcare sector  
            'Pharmaceuticals': 'Healthcare',
            'Biotechnology': 'Healthcare',
            'Medical Equipment & Supplies': 'Healthcare',
            'Healthcare Services': 'Healthcare',
            
            # Financial sector
            'Banks': 'Financial Services',
            'Insurance': 'Financial Services',
            'Capital Markets': 'Financial Services',
            'Data Processing & Outsourced Services': 'Financial Services',
            
            # Consumer sector
            'Internet & Direct Marketing Retail': 'Consumer Discretionary',
            'Automobiles': 'Consumer Discretionary',
            'Media & Entertainment': 'Consumer Discretionary',
            'Hotels, Restaurants & Leisure': 'Consumer Discretionary',
            
            # Energy sector
            'Oil, Gas & Coal': 'Energy',
            'Alternative Energy': 'Energy',
            
            # Industrial sector
            'Aerospace & Defense': 'Industrials',
            'Construction & Engineering': 'Industrials',
            'Machinery': 'Industrials',
            
            # Communication sector
            'Interactive Media & Services': 'Communication Services',
            'Diversified Telecommunication Services': 'Communication Services',
            'Wireless Telecommunication Services': 'Communication Services',
        }
        return industry_sector_map.get(industry_name, 'Technology')  # Default to Technology