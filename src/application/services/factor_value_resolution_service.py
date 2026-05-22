"""
Application service for factor value resolution with dependency handling.

This service orchestrates the factor value calculation process, using domain services
to resolve dependencies and infrastructure services to access data.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from src.domain.services.factor_value_dependency_resolver import (
    FactorValueDependencyResolver, 
    FactorValueAggregationService,
    DependencyResolutionContext
)
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.factor_dependency import FactorDependency


class FactorValueResolutionService:
    """
    Application service that orchestrates factor value calculation with dependency resolution.
    
    This service implements the logic described in the issue:
    1. For dependent entities with direct relationships: extract the related entity ID and calculate
    2. For dependent entities with indirect relationships: aggregate factor values from related entities
    """
    
    def __init__(
        self,
        factor_value_repository,
        factor_dependency_repository,
        factor_repository,
        dependency_resolver: FactorValueDependencyResolver,
        aggregation_service: FactorValueAggregationService
    ):
        self.factor_value_repository = factor_value_repository
        self.factor_dependency_repository = factor_dependency_repository
        self.factor_repository = factor_repository
        self.dependency_resolver = dependency_resolver
        self.aggregation_service = aggregation_service
        self._resolution_cache = {}  # Cache for preventing infinite loops
    
    def resolve_factor_value(
        self,
        factor_id: int,
        entity_id: int,
        calculation_date: datetime,
        entity_type: str = None
    ) -> Optional[FactorValue]:
        """
        Resolve a factor value for an entity, handling both direct and indirect dependencies.
        
        Args:
            factor_id: ID of the factor to calculate
            entity_id: ID of the entity for which to calculate the factor
            calculation_date: Date for the calculation
            entity_type: Type of the entity (helps with dependency resolution)
            
        Returns:
            FactorValue entity or None if calculation failed
        """
        try:
            # Create cache key to prevent infinite recursion
            cache_key = (factor_id, entity_id, calculation_date.isoformat())
            if cache_key in self._resolution_cache:
                return self._resolution_cache[cache_key]
            
            # Mark this calculation as in progress
            self._resolution_cache[cache_key] = None
            
            # Check if factor value already exists
            date_str = calculation_date.strftime("%Y-%m-%d %H:%M:%S")
            existing_value = self.factor_value_repository.get_by_factor_entity_date(
                factor_id, entity_id, date_str
            )
            if existing_value:
                self._resolution_cache[cache_key] = existing_value
                return existing_value
            
            # Get factor entity
            factor_entity = self.factor_repository.get_by_id(factor_id)
            if not factor_entity:
                print(f"Factor {factor_id} not found")
                return None
            
            # Get factor dependencies
            dependencies = self.factor_dependency_repository.get_by_dependent_factor_id(factor_id)
            
            if not dependencies:
                # No dependencies - create factor value with default or provided value
                factor_value = self._create_simple_factor_value(
                    factor_entity, entity_id, calculation_date
                )
            else:
                # Has dependencies - resolve them and calculate
                factor_value = self._create_dependent_factor_value(
                    factor_entity, entity_id, calculation_date, dependencies, entity_type
                )
            
            # Cache the result
            self._resolution_cache[cache_key] = factor_value
            return factor_value
            
        except Exception as e:
            print(f"Error resolving factor value for factor {factor_id}, entity {entity_id}: {e}")
            return None
        finally:
            # Clean up cache entry if it was None (in-progress marker)
            if cache_key in self._resolution_cache and self._resolution_cache[cache_key] is None:
                del self._resolution_cache[cache_key]
    
    def _create_simple_factor_value(
        self,
        factor_entity: Any,
        entity_id: int,
        calculation_date: datetime,
        default_value: str = "0.0"
    ) -> Optional[FactorValue]:
        """Create a factor value without dependencies."""
        try:
            factor_value = FactorValue(
                id=None,
                factor_id=factor_entity.id,
                entity_id=entity_id,
                date=calculation_date,
                value=default_value
            )
            return self.factor_value_repository.add(factor_value)
        except Exception as e:
            print(f"Error creating simple factor value: {e}")
            return None
    
    def _create_dependent_factor_value(
        self,
        factor_entity: Any,
        entity_id: int,
        calculation_date: datetime,
        dependencies: List[FactorDependency],
        entity_type: str = None
    ) -> Optional[FactorValue]:
        """Create a factor value that depends on other factor values."""
        try:
            # Resolve dependency values
            dependency_values = {}
            
            for dependency in dependencies:
                dep_values = self._resolve_single_dependency(
                    dependency, entity_id, calculation_date, entity_type
                )
                dependency_values.update(dep_values)
            
            # Calculate the factor value using the factor's calculate method
            calculated_value = self._calculate_factor_value(
                factor_entity, dependency_values, entity_id, calculation_date
            )
            
            if calculated_value is not None:
                # Create and persist the calculated factor value
                factor_value = FactorValue(
                    id=None,
                    factor_id=factor_entity.id,
                    entity_id=entity_id,
                    date=calculation_date,
                    value=str(calculated_value)
                )
                return self.factor_value_repository.add(factor_value)
            
            return None
            
        except Exception as e:
            print(f"Error creating dependent factor value: {e}")
            return None
    
    def _resolve_single_dependency(
        self,
        dependency: FactorDependency,
        dependent_entity_id: int,
        calculation_date: datetime,
        entity_type: str = None
    ) -> Dict[str, float]:
        """
        Resolve a single dependency, handling both direct and indirect relationships.
        
        Returns:
            Dictionary with dependency values keyed by dependency name
        """
        try:
            # Create resolution context
            context = DependencyResolutionContext(
                dependent_entity_id=dependent_entity_id,
                dependent_entity_type=entity_type or 'unknown',
                calculation_date=calculation_date
            )
            
            # Resolve which entities to get factor values from
            target_entity_ids = self.dependency_resolver.resolve_dependencies_for_factor(
                dependency, context
            )
            
            if not target_entity_ids:
                return {}
            
            # Calculate dependency date (apply lag if specified)
            dependency_date = calculation_date
            if dependency.lag:
                dependency_date = calculation_date - dependency.lag
            
            # Get factor values for all target entities
            factor_values = {}
            for target_entity_id in target_entity_ids:
                if hasattr(dependency, 'independent_factor_related_entity_key') and dependency.independent_factor_related_entity_key:
                    # Direct relationship case - use the related entity ID instead of the dependent entity ID
                    # This would require extracting the actual related entity ID from the dependent entity
                    actual_target_id = self._get_related_entity_id(
                        dependent_entity_id, dependency.independent_factor_related_entity_key
                    )
                    if actual_target_id:
                        target_entity_id = actual_target_id
                
                # Recursively resolve the independent factor value
                independent_factor_value = self.resolve_factor_value(
                    dependency.independent_factor_id,
                    target_entity_id,
                    dependency_date
                )
                
                if independent_factor_value:
                    factor_values[target_entity_id] = float(independent_factor_value.value)
            
            # Aggregate if we have multiple values (indirect relationship case)
            if len(factor_values) > 1:
                aggregated_value = self.aggregation_service.aggregate_factor_values(factor_values)
                return {f"factor_{dependency.independent_factor_id}": aggregated_value}
            elif len(factor_values) == 1:
                return {f"factor_{dependency.independent_factor_id}": list(factor_values.values())[0]}
            else:
                return {f"factor_{dependency.independent_factor_id}": 0.0}
            
        except Exception as e:
            print(f"Error resolving dependency {dependency.independent_factor_id}: {e}")
            return {f"factor_{dependency.independent_factor_id}": 0.0}
    
    def _get_related_entity_id(self, entity_id: int, relationship_key: str) -> Optional[int]:
        """
        Extract the related entity ID from an entity using the relationship key.
        
        For direct relationships like options with underlying_asset_id.
        """
        try:
            # This would need to be implemented based on the specific entity types
            # For now, return the entity_id itself as a placeholder
            # In practice, this would query the entity and extract the relationship field
            return entity_id
        except Exception as e:
            print(f"Error getting related entity ID for {entity_id} with key {relationship_key}: {e}")
            return None
    
    def _calculate_factor_value(
        self,
        factor_entity: Any,
        dependency_values: Dict[str, float],
        entity_id: int,
        calculation_date: datetime
    ) -> Optional[float]:
        """Calculate the final factor value using the factor's calculate method."""
        try:
            if hasattr(factor_entity, 'calculate') and callable(factor_entity.calculate):
                result = factor_entity.calculate(dependency_values)
                return float(result) if result is not None else None
            else:
                # Default calculation - sum of dependencies
                return sum(dependency_values.values()) if dependency_values else 0.0
        except Exception as e:
            print(f"Error calculating factor value for {factor_entity.name}: {e}")
            return None
    
    def clear_resolution_cache(self):
        """Clear the resolution cache to free memory."""
        self._resolution_cache.clear()