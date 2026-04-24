"""
src/domain/entities/factor/dynamic_dependency_requirements.py

Domain entity for defining dynamic dependency requirements for factors.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from datetime import timedelta


@dataclass
class DependencyRequirements:
    """
    Domain entity defining dynamic dependency requirements for a factor.
    
    This replaces static dependencies in the FactorDependency table with 
    flexible, date-aware dependency discovery rules.
    """
    
    # Basic requirements
    required_groups: List[str]  # e.g., ["price", "volume"]
    required_subgroups: Optional[List[str]] = None  # e.g., ["mid_price", "close"]
    required_factor_names: Optional[List[str]] = None  # e.g., ["open", "close"]
    
    # Data quality requirements
    min_sources: int = 1  # Minimum number of data sources required
    max_sources: Optional[int] = None  # Maximum sources to consider (performance)
    max_age_days: int = 1  # Maximum age of dependency data in days
    
    # Source preferences 
    preferred_sources: Optional[List[str]] = None  # e.g., ["ibkr", "fmp", "yahoo"]
    excluded_sources: Optional[List[str]] = None  # Sources to avoid
    
    # Temporal requirements
    lag_requirements: Optional[Dict[str, timedelta]] = None  # e.g., {"start_price": timedelta(days=1)}
    frequency_compatibility: Optional[List[str]] = None  # Compatible frequencies
    
    # Fallback strategies
    fallback_strategies: Optional[List[str]] = None  # e.g., ["use_close_if_no_mid", "single_source_ok"]
    allow_single_source: bool = False  # Allow calculation with just one source
    allow_older_data: bool = False  # Allow data older than max_age_days if nothing else available
    
    # Entity relationship requirements
    entity_relationship_keys: Optional[List[str]] = None  # e.g., ["underlying_asset_id", "currency_id"]
    
    def __post_init__(self):
        """Validate dependency requirements."""
        if not self.required_groups:
            raise ValueError("At least one required_group must be specified")
        
        if self.min_sources < 1:
            raise ValueError("min_sources must be at least 1")
            
        if self.max_sources and self.max_sources < self.min_sources:
            raise ValueError("max_sources cannot be less than min_sources")
            
        if self.max_age_days < 0:
            raise ValueError("max_age_days cannot be negative")

    def matches_factor(self, factor: Any) -> bool:
        """
        Check if a factor matches these dependency requirements.
        
        Args:
            factor: Factor entity to check
            
        Returns:
            True if factor matches requirements, False otherwise
        """
        # Check required groups
        factor_group = getattr(factor, 'group', '')
        if factor_group not in self.required_groups:
            return False
            
        # Check required subgroups if specified
        if self.required_subgroups:
            factor_subgroup = getattr(factor, 'subgroup', '')
            if factor_subgroup not in self.required_subgroups:
                return False
        
        # Check required factor names if specified
        if self.required_factor_names:
            factor_name = getattr(factor, 'name', '')
            if factor_name not in self.required_factor_names:
                return False
        
        # Check source preferences
        factor_source = getattr(factor, 'source', '')
        if self.excluded_sources and factor_source in self.excluded_sources:
            return False
            
        return True

    def get_source_priority_score(self, source: str) -> int:
        """
        Get priority score for a data source (higher = better).
        
        Args:
            source: Data source name
            
        Returns:
            Priority score (0-100)
        """
        if self.excluded_sources and source in self.excluded_sources:
            return 0
            
        if self.preferred_sources:
            if source in self.preferred_sources:
                # Higher priority for earlier sources in preferred list
                index = self.preferred_sources.index(source)
                return 100 - (index * 10)
            else:
                # Lower priority for non-preferred sources
                return 20
        
        # Default priority if no preferences specified
        return 50

    def is_compatible_frequency(self, frequency: str) -> bool:
        """
        Check if a frequency is compatible with these requirements.
        
        Args:
            frequency: Frequency string to check
            
        Returns:
            True if compatible, False otherwise
        """
        if not self.frequency_compatibility:
            return True  # No restrictions
            
        return frequency in self.frequency_compatibility

    def should_apply_fallback(self, available_count: int, sources: Set[str]) -> bool:
        """
        Determine if fallback strategies should be applied.
        
        Args:
            available_count: Number of available dependencies found
            sources: Set of available source names
            
        Returns:
            True if fallback strategies should be applied
        """
        if available_count < self.min_sources:
            return True
            
        if not self.allow_single_source and len(sources) == 1 and self.min_sources > 1:
            return True
            
        return False

    def __str__(self) -> str:
        return (f"DependencyRequirements(groups={self.required_groups}, "
                f"min_sources={self.min_sources}, max_age_days={self.max_age_days})")

    def __repr__(self) -> str:
        return (f"DependencyRequirements(required_groups={self.required_groups}, "
                f"required_subgroups={self.required_subgroups}, "
                f"min_sources={self.min_sources}, "
                f"preferred_sources={self.preferred_sources})")