"""
IBKR Sector Repository - Interactive Brokers implementation for Sectors.

This repository handles sector data for IBKR financial entities, applying IBKR-specific 
business rules and sector classifications.
"""

import os
from typing import Optional, List

from src.domain.entities.sector import Sector
from src.domain.ports.sector_port import SectorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.mappers.sector_mapper import SectorMapper


class IBKRSectorRepository(BaseIBKRRepository, SectorPort):
    """
    IBKR implementation of SectorPort for sector data management.
    """

    def __init__(self, ibkr_client, factory, mapper: SectorMapper = None):
        """
        Initialize IBKR Sector Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (required)
            mapper: Sector mapper for entity/model conversion (optional, will create if not provided)
        """
        self.factory = factory
        if factory:
            self.local_repo = self.factory.sector_local_repo
        else:
            raise ValueError("Factory is required for IBKRSectorRepository")
        self.mapper = mapper or SectorMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for Sector."""
        return Sector

    @property
    def model_class(self):
        """Return the model entity class for Sector."""
        return self.mapper.model_class

    def _create_or_get(self, name: str) -> Optional[Sector]:
        """
        Get or create a sector by name using IBKR sector classifications.
        
        Args:
            name: Sector name (e.g., 'Technology', 'Healthcare', 'Financial Services')
            
        Returns:
            Sector entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_name(name)
            if existing:
                return existing
            
            # 2. Create new sector with IBKR-specific description
            description = self._get_sector_description(name)
            
            # 3. Use local repository to create the sector
            return self.local_repo.get_or_create(
                name=name,
                classification_system='IBKR',  # IBKR uses its own classification
                description=description
            )
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for sector {name}: {e}_{os.path.abspath(__file__)}")
            return None

    def get_by_name(self, name: str) -> Optional[Sector]:
        """Get sector by name (delegates to local repository)."""
        return self.local_repo.get_by_name(name)

    def get_by_id(self, entity_id: int) -> Optional[Sector]:
        """Get sector by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Sector]:
        """Get all sectors (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Sector) -> Optional[Sector]:
        """Add sector entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Sector) -> Optional[Sector]:
        """Update sector entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete sector entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def get_by_classification_system(self, classification_system: str) -> List[Sector]:
        """Get sectors by classification system (delegates to local repository)."""
        return self.local_repo.get_by_classification_system(classification_system)

    def _get_sector_description(self, sector_name: str) -> str:
        """Get detailed description for IBKR sector classifications."""
        sector_descriptions = {
            'Technology': 'Companies involved in the design, development, and support of computer operating systems, equipment, and services',
            'Healthcare': 'Companies involved in the research, development, production, and marketing of products and services related to health and medical care',
            'Financial Services': 'Companies that provide financial services including banking, insurance, real estate, and investment services',
            'Consumer Discretionary': 'Companies that sell non-essential goods and services that consumers may forego during tough economic times',
            'Consumer Staples': 'Companies that produce or sell essential products that people need regardless of economic conditions',
            'Energy': 'Companies involved in the exploration, production, marketing, refining, and/or transportation of oil, natural gas, and renewable energy',
            'Industrials': 'Companies involved in manufacturing and distribution of capital goods used in production and construction',
            'Materials': 'Companies involved in the discovery, development, and processing of raw materials',
            'Communication Services': 'Companies that provide communication services through various mediums including internet, phone, and media content',
            'Utilities': 'Companies that provide essential services such as electricity, natural gas, water, and waste management services',
            'Real Estate': 'Companies involved in real estate development, operation, and investment trust activities'
        }
        return sector_descriptions.get(sector_name, f"{sector_name} sector classification from IBKR")

    def get_ibkr_sector_mapping(self) -> dict:
        """
        Get IBKR-specific sector mapping for companies.
        This would typically come from IBKR API classifications.
        
        Returns:
            Dictionary mapping IBKR sector codes to sector names
        """
        return {
            'TECH': 'Technology',
            'HLTH': 'Healthcare', 
            'FINL': 'Financial Services',
            'CDIS': 'Consumer Discretionary',
            'CSTAP': 'Consumer Staples',
            'ENRG': 'Energy',
            'IND': 'Industrials',
            'MAT': 'Materials',
            'COMM': 'Communication Services',
            'UTIL': 'Utilities',
            'REAL': 'Real Estate'
        }

    def get_sector_for_symbol(self, symbol: str) -> Optional[Sector]:
        """
        Get sector classification for a specific stock symbol using IBKR data.
        In a real implementation, this would query IBKR API for sector information.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            Sector entity or None if not found
        """
        # Mock sector mapping for common symbols
        symbol_sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Communication Services',
            'AMZN': 'Consumer Discretionary',
            'TSLA': 'Consumer Discretionary',
            'NVDA': 'Technology',
            'META': 'Communication Services',
            'JPM': 'Financial Services',
            'JNJ': 'Healthcare',
            'V': 'Financial Services',
            'PG': 'Consumer Staples',
            'UNH': 'Healthcare',
            'HD': 'Consumer Discretionary',
            'DIS': 'Communication Services',
            'BAC': 'Financial Services'
        }
        
        sector_name = symbol_sector_map.get(symbol, 'Technology')
        return self._create_or_get(sector_name)