"""
src/domain/entities/factor/factor_dependency_resolver.py

Enhanced factor dependency resolution system with discriminator-based lookup.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
import inspect
from dataclasses import dataclass

from src.domain.entities.factor.factor_dependency import (
    FactorDependencyGraph, 
    FactorDependencyRegistry,
    FactorDiscriminator,
    FactorReference,
    FactorDependency,
    FactorDependencyValidator,
    InMemoryFactorDependencyRegistry
)

if TYPE_CHECKING:
    from src.domain.entities.factor.factor import Factor


@dataclass
class DependencyResolutionContext:
    """
    Context for dependency resolution containing execution metadata.
    
    Timestamps and execution context are handled here, not in the dependency definitions.
    """
    timestamp: datetime
    instrument_id: Optional[int] = None
    entity_id: Optional[int] = None
    resolution_depth: int = 0
    max_depth: int = 10  # Prevent infinite recursion
    resolved_cache: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.resolved_cache is None:
            self.resolved_cache = {}


class FactorDependencyResolutionError(Exception):
    """Raised when factor dependency resolution fails."""
    pass


class FactorDependencyResolver:
    """
    Resolves factor dependencies using discriminator-based lookup with recursive resolution.
    
    This class handles the complete dependency resolution pipeline:
    1. Extract dependencies from factor class definitions
    2. Resolve dependencies recursively using discriminators
    3. Call factor calculate() methods with resolved values
    4. Handle caching and cycle detection
    """
    
    def __init__(
        self, 
        registry: FactorDependencyRegistry,
        data_source_resolver: Optional[Any] = None
    ):
        """
        Initialize dependency resolver.
        
        Args:
            registry: Factor registry for discriminator-based lookup
            data_source_resolver: External data source for factor values (e.g., IBKR)
        """
        self.registry = registry
        self.data_source_resolver = data_source_resolver
        self.validator = FactorDependencyValidator(registry)
    
    def resolve_dependencies(
        self, 
        factor: 'Factor',
        context: DependencyResolutionContext
    ) -> Dict[str, Any]:
        """
        Resolve all dependencies for a factor using discriminator-based lookup.
        
        Args:
            factor: Factor entity to resolve dependencies for
            context: Resolution context with timestamp and metadata
            
        Returns:
            Dictionary mapping parameter names to resolved values
            
        Raises:
            FactorDependencyResolutionError: If required dependencies cannot be resolved
        """
        if context.resolution_depth >= context.max_depth:
            raise FactorDependencyResolutionError(
                f"Maximum resolution depth ({context.max_depth}) exceeded for factor {factor.name}"
            )
        
        # Extract dependency graph from factor
        dependency_graph = self._extract_factor_dependencies(factor)
        
        if not dependency_graph.has_dependencies():
            return {}
        
        resolved_values = {}
        missing_required = []
        
        for param_name, dependency in dependency_graph.dependencies.items():
            try:
                # Create cache key for this dependency at this timestamp
                cache_key = self._create_cache_key(dependency, context)
                
                # Check cache first
                if cache_key in context.resolved_cache:
                    resolved_values[param_name] = context.resolved_cache[cache_key]
                    continue
                
                # Resolve dependency value
                resolved_value = self._resolve_single_dependency(dependency, context)
                
                if resolved_value is not None:
                    resolved_values[param_name] = resolved_value
                    context.resolved_cache[cache_key] = resolved_value
                elif dependency.required:
                    missing_required.append(param_name)
                elif dependency.default_value is not None:
                    resolved_values[param_name] = dependency.default_value
                
            except Exception as e:
                if dependency.required:
                    missing_required.append(param_name)
                    print(f"Error resolving required dependency {param_name}: {e}")
                else:
                    print(f"Error resolving optional dependency {param_name}: {e}")
        
        if missing_required:
            raise FactorDependencyResolutionError(
                f"Failed to resolve required dependencies for {factor.name}: {missing_required}"
            )
        
        return resolved_values
    
    def calculate_factor_with_dependencies(
        self, 
        factor: 'Factor',
        context: DependencyResolutionContext,
        **additional_params
    ) -> Optional[Any]:
        """
        Calculate factor value by resolving dependencies and calling calculate method.
        
        Args:
            factor: Factor to calculate
            context: Resolution context
            additional_params: Additional parameters for calculation
            
        Returns:
            Calculated factor value or None if calculation failed
        """
        try:
            # Resolve all dependencies
            resolved_dependencies = self.resolve_dependencies(factor, context)
            
            # Merge with additional parameters
            all_params = {**resolved_dependencies, **additional_params}
            
            # Call factor's calculate method
            return self._call_factor_calculate_method(factor, all_params)
            
        except Exception as e:
            print(f"Error calculating factor {factor.name} with dependencies: {e}")
            return None
    
    def _extract_factor_dependencies(self, factor: 'Factor') -> FactorDependencyGraph:
        """
        Extract dependencies from factor class using the new discriminator format.
        
        Supports both the new discriminator format and legacy dependency formats.
        """
        dependencies_graph = FactorDependencyGraph()
        
        try:
            factor_class = factor.__class__
            
            # 1. Check for new discriminator-based dependencies attribute
            if hasattr(factor_class, 'dependencies'):
                deps_data = getattr(factor_class, 'dependencies')
                if isinstance(deps_data, dict):
                    # Check if this is the new discriminator format
                    if self._is_discriminator_format(deps_data):
                        dependencies_graph = FactorDependencyGraph.from_dependencies_dict(deps_data)
                    else:
                        # Legacy format - convert to discriminator format
                        dependencies_graph = self._convert_legacy_dependencies(deps_data, factor)
            
            # 2. If no explicit dependencies, analyze calculate method parameters
            if not dependencies_graph.has_dependencies():
                dependencies_graph = self._infer_dependencies_from_method(factor)
        
        except Exception as e:
            print(f"Error extracting dependencies for {factor.name}: {e}")
        
        return dependencies_graph
    
    def _is_discriminator_format(self, deps_data: Dict[str, Any]) -> bool:
        """Check if dependencies data uses the new discriminator format."""
        for dep_data in deps_data.values():
            if isinstance(dep_data, dict) and "factor" in dep_data:
                factor_data = dep_data["factor"]
                if isinstance(factor_data, dict) and "discriminator" in factor_data:
                    return True
        return False
    
    def _convert_legacy_dependencies(self, legacy_deps: Dict[str, Any], factor: 'Factor') -> FactorDependencyGraph:
        """Convert legacy dependency format to discriminator-based format."""
        graph = FactorDependencyGraph()
        
        for param_name, dep_info in legacy_deps.items():
            if isinstance(dep_info, str):
                # Simple string dependency - create basic discriminator
                discriminator = FactorDiscriminator(
                    code=f"LEGACY_{dep_info.upper()}",
                    version="v1"
                )
                factor_ref = FactorReference(
                    discriminator=discriminator,
                    name=dep_info,
                    group="Legacy",
                    source="inferred"
                )
            elif isinstance(dep_info, dict):
                # Dictionary dependency - extract what we can
                name = dep_info.get('name', param_name)
                discriminator = FactorDiscriminator(
                    code=f"LEGACY_{name.upper().replace(' ', '_')}",
                    version="v1"
                )
                factor_ref = FactorReference(
                    discriminator=discriminator,
                    name=name,
                    group=dep_info.get('group', 'Legacy'),
                    subgroup=dep_info.get('subgroup'),
                    source=dep_info.get('source', 'inferred')
                )
            else:
                continue
            
            dependency = FactorDependency(
                parameter_name=param_name,
                factor_reference=factor_ref,
                required=True  # Assume required for legacy
            )
            
            graph.add_dependency(dependency)
        
        return graph
    
    def _infer_dependencies_from_method(self, factor: 'Factor') -> FactorDependencyGraph:
        """Infer dependencies by analyzing calculate method parameters."""
        graph = FactorDependencyGraph()
        
        try:
            # Look for calculate methods
            calculate_methods = [method for method in dir(factor.__class__) 
                               if method.startswith('calculate') and callable(getattr(factor.__class__, method))]
            
            for method_name in calculate_methods:
                method = getattr(factor.__class__, method_name)
                if hasattr(method, '__code__'):
                    # Get method signature
                    sig = inspect.signature(method)
                    
                    for param_name, param in sig.parameters.items():
                        if param_name in ['self', 'kwargs', 'args']:
                            continue
                        
                        # Infer discriminator from parameter name
                        discriminator = FactorDiscriminator(
                            code=f"INFERRED_{param_name.upper()}",
                            version="v1"
                        )
                        
                        factor_ref = FactorReference(
                            discriminator=discriminator,
                            name=param_name.replace('_', ' ').title(),
                            group="Inferred",
                            source="method_signature"
                        )
                        
                        dependency = FactorDependency(
                            parameter_name=param_name,
                            factor_reference=factor_ref,
                            required=param.default == inspect.Parameter.empty
                        )
                        
                        graph.add_dependency(dependency)
                
                break  # Use first calculate method found
        
        except Exception as e:
            print(f"Error inferring dependencies from method for {factor.name}: {e}")
        
        return graph
    
    def _resolve_single_dependency(
        self, 
        dependency: FactorDependency, 
        context: DependencyResolutionContext
    ) -> Optional[Any]:
        """
        Resolve a single dependency using discriminator-based lookup.
        
        This is where the actual dependency resolution magic happens.
        """
        try:
            discriminator = dependency.factor_reference.discriminator
            
            # 1. Try to resolve factor from registry using discriminator
            dependent_factor = self.registry.resolve_factor(discriminator)
            
            if dependent_factor:
                # 2. Recursively resolve dependencies for this factor
                nested_context = DependencyResolutionContext(
                    timestamp=context.timestamp,
                    instrument_id=context.instrument_id,
                    entity_id=context.entity_id,
                    resolution_depth=context.resolution_depth + 1,
                    max_depth=context.max_depth,
                    resolved_cache=context.resolved_cache
                )
                
                # 3. Calculate the dependent factor value
                factor_value = self.calculate_factor_with_dependencies(dependent_factor, nested_context)
                
                if factor_value is not None:
                    return factor_value
            
            # 4. If factor not in registry or calculation failed, try data source
            if self.data_source_resolver:
                return self._resolve_from_data_source(dependency, context)
            
            return None
            
        except Exception as e:
            print(f"Error resolving dependency {dependency.parameter_name}: {e}")
            return None
    
    def _resolve_from_data_source(
        self, 
        dependency: FactorDependency, 
        context: DependencyResolutionContext
    ) -> Optional[Any]:
        """
        Resolve dependency from external data source (e.g., IBKR API).
        
        This integrates with the existing IBKR factor value repository.
        """
        if not self.data_source_resolver:
            return None
        
        try:
            # Extract discriminator information
            discriminator = dependency.factor_reference.discriminator
            factor_ref = dependency.factor_reference
            
            # Map discriminator to data source query
            if hasattr(self.data_source_resolver, 'resolve_by_discriminator'):
                return self.data_source_resolver.resolve_by_discriminator(
                    discriminator=discriminator,
                    factor_reference=factor_ref,
                    timestamp=context.timestamp,
                    entity_id=context.entity_id,
                    instrument_id=context.instrument_id
                )
            
            # Fallback to legacy resolution if available
            if hasattr(self.data_source_resolver, 'resolve_dependency'):
                return self.data_source_resolver.resolve_dependency(
                    name=factor_ref.name or discriminator.code,
                    source=factor_ref.source,
                    timestamp=context.timestamp,
                    entity_id=context.entity_id
                )
            
            return None
            
        except Exception as e:
            print(f"Error resolving dependency from data source: {e}")
            return None
    
    def _create_cache_key(self, dependency: FactorDependency, context: DependencyResolutionContext) -> str:
        """Create cache key for resolved dependency."""
        discriminator_key = dependency.factor_reference.discriminator.to_key()
        timestamp_key = context.timestamp.strftime("%Y%m%d_%H%M%S")
        entity_key = f"entity_{context.entity_id}" if context.entity_id else "no_entity"
        
        return f"{discriminator_key}_{timestamp_key}_{entity_key}"
    
    def _call_factor_calculate_method(self, factor: 'Factor', resolved_params: Dict[str, Any]) -> Optional[Any]:
        """
        Call the appropriate calculate method on factor with resolved parameters.
        
        This is enhanced from the original IBKRFactorValueRepository implementation.
        """
        try:
            factor_class = factor.__class__
            
            # Look for calculate methods in order of preference
            calculate_methods = [
                'calculate',
                'calculate_forward_price',  # For futures
                'calculate_momentum',
                'calculate_price',
                'calculate_value',
                'compute'
            ]
            
            for method_name in calculate_methods:
                if hasattr(factor_class, method_name):
                    method = getattr(factor, method_name)
                    if callable(method):
                        try:
                            # Get method signature to match parameters
                            sig = inspect.signature(method)
                            method_params = {}
                            
                            # Map resolved parameters to method signature
                            for param_name, param in sig.parameters.items():
                                if param_name == 'self':
                                    continue
                                elif param_name in resolved_params:
                                    method_params[param_name] = resolved_params[param_name]
                                elif param.default != inspect.Parameter.empty:
                                    # Use default value for optional parameters
                                    continue
                                else:
                                    # Required parameter not available
                                    print(f"Required parameter {param_name} not available for {factor.name}.{method_name}")
                                    break
                            else:
                                # All required parameters available - call method
                                result = method(**method_params)
                                if result is not None:
                                    return result
                        
                        except Exception as method_error:
                            print(f"Error calling {method_name} on {factor.name}: {method_error}")
                            continue
            
            print(f"No suitable calculate method found for {factor.name}")
            return None
            
        except Exception as e:
            print(f"Error calling factor calculate method for {factor.name}: {e}")
            return None