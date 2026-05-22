"""
Domain service for resolving factor value dependencies.

This service handles both direct and indirect entity dependencies for factor calculation:
1. Direct dependencies: Derivative entities that contain the related entity ID (e.g., options with underlying_asset_id)
2. Indirect dependencies: Entities that need aggregation of related entities (e.g., portfolios aggregating holdings)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DependencyResolutionContext:
    """Context for dependency resolution containing entity information and calculation date."""
    
    dependent_entity_id: int
    dependent_entity_type: str  # e.g., 'portfolio', 'option', 'future'
    calculation_date: datetime
    lag_adjustments: Dict[str, Any] = None


class EntityRelationshipResolver(Protocol):
    """Protocol for resolving entity relationships."""
    
    def get_related_entities(self, entity_id: int, entity_type: str, relationship_type: str) -> List[int]:
        """Get related entity IDs for a given entity and relationship type."""
        ...


class FactorValueDependencyResolver:
    """
    Domain service for resolving factor dependencies based on entity relationships.
    
    This service implements the logic described in the issue:
    - For direct relationships (e.g., option → underlying asset): Use the related entity ID from the dependent entity
    - For indirect relationships (e.g., portfolio → holdings): Query for related entities and aggregate
    """
    
    def __init__(self, entity_resolver: EntityRelationshipResolver):
        self.entity_resolver = entity_resolver
    
    def resolve_dependencies_for_factor(
        self, 
        factor_dependency: Any,  # FactorDependency entity
        context: DependencyResolutionContext
    ) -> List[int]:
        """
        Resolve the entity IDs that need to be considered for calculating a dependent factor value.
        
        Args:
            factor_dependency: The factor dependency entity containing the relationship info
            context: Context for the dependency resolution
            
        Returns:
            List of entity IDs that should be used for calculating the independent factor values
        """
        # Check if the dependency has a direct entity relationship key
        if (hasattr(factor_dependency, 'independent_factor_related_entity_key') 
            and factor_dependency.independent_factor_related_entity_key):
            
            # Direct relationship case (e.g., option has underlying_asset_id)
            return self._resolve_direct_dependency(factor_dependency, context)
        else:
            # Indirect relationship case (e.g., portfolio needs to aggregate holdings)
            return self._resolve_indirect_dependency(factor_dependency, context)
    
    def _resolve_direct_dependency(
        self, 
        factor_dependency: Any, 
        context: DependencyResolutionContext
    ) -> List[int]:
        """
        Resolve dependencies for entities that contain the related entity ID directly.
        
        For example, an option entity has an 'underlying_asset_id' field that points
        to the company share it depends on.
        """
        # The dependent entity itself contains the reference to the independent entity
        # In this case, we need to get the value of the related entity field from the dependent entity
        
        # For now, return the dependent entity ID as it contains the relationship
        # The actual related entity ID would be extracted from the dependent entity's attributes
        # This would be implemented by the specific factor calculation logic
        return [context.dependent_entity_id]
    
    def _resolve_indirect_dependency(
        self, 
        factor_dependency: Any, 
        context: DependencyResolutionContext
    ) -> List[int]:
        """
        Resolve dependencies for entities that require aggregation of related entities.
        
        For example, a portfolio doesn't contain holding IDs directly, but holdings
        contain the portfolio_id, so we need to query for all holdings related to this portfolio.
        """
        relationship_mapping = {
            'portfolio': 'holdings',  # Portfolio aggregates its holdings
            'index': 'constituents',  # Index aggregates its constituent securities
            # Add more mappings as needed
        }
        
        relationship_type = relationship_mapping.get(context.dependent_entity_type)
        if not relationship_type:
            # No known indirect relationship for this entity type
            return []
        
        # Get all related entities (e.g., all holdings for this portfolio)
        related_entity_ids = self.entity_resolver.get_related_entities(
            entity_id=context.dependent_entity_id,
            entity_type=context.dependent_entity_type,
            relationship_type=relationship_type
        )
        
        return related_entity_ids


class FactorValueAggregationService:
    """
    Service for aggregating factor values from multiple related entities.
    
    This service handles the calculation of factor values that depend on aggregating
    values from multiple related entities (e.g., portfolio value from holdings).
    """
    
    def aggregate_factor_values(
        self,
        factor_values: Dict[int, float],  # entity_id -> factor_value
        aggregation_type: str = 'sum'
    ) -> float:
        """
        Aggregate multiple factor values into a single value.
        
        Args:
            factor_values: Dictionary mapping entity IDs to their factor values
            aggregation_type: Type of aggregation ('sum', 'average', 'weighted_sum', etc.)
            
        Returns:
            Aggregated factor value
        """
        if not factor_values:
            return 0.0
        
        values = list(factor_values.values())
        
        if aggregation_type == 'sum':
            return sum(values)
        elif aggregation_type == 'average':
            return sum(values) / len(values) if values else 0.0
        elif aggregation_type == 'max':
            return max(values)
        elif aggregation_type == 'min':
            return min(values)
        else:
            # Default to sum for unknown aggregation types
            return sum(values)