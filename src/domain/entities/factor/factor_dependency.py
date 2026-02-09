"""
src/domain/entities/factor/factor_dependency.py

Domain entities for factor dependency management using discriminator-based resolution.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


@dataclass
class FactorDiscriminator:
    """
    Stable discriminator for factor identification.
    
    Uses code + version for technical resolution while supporting 
    human-readable metadata.
    """
    code: str  # Technical stable identifier (e.g., "MARKET_SPOT_PRICE")
    version: str  # Version for discriminator evolution (e.g., "v1")
    
    def __post_init__(self):
        if not self.code or not self.version:
            raise ValueError("Both code and version are required for discriminator")
    
    def to_key(self) -> str:
        """Generate unique key for discriminator lookup."""
        return f"{self.code}:{self.version}"
    
    @classmethod
    def from_key(cls, key: str) -> 'FactorDiscriminator':
        """Create discriminator from key string."""
        try:
            code, version = key.split(":", 1)
            return cls(code=code, version=version)
        except ValueError:
            raise ValueError(f"Invalid discriminator key format: {key}")


@dataclass
class FactorReference:
    """
    Complete factor reference with discriminator and optional human metadata.
    
    The discriminator is used for stable technical resolution, while
    the metadata provides human-readable context as hints only.
    """
    discriminator: FactorDiscriminator
    name: Optional[str] = None  # Human hint only
    group: Optional[str] = None  # Human hint only
    subgroup: Optional[str] = None  # Human hint only
    source: Optional[str] = None  # Human hint only
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "discriminator": {
                "code": self.discriminator.code,
                "version": self.discriminator.version
            },
            "name": self.name,
            "group": self.group,
            "subgroup": self.subgroup,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FactorReference':
        """Create from dictionary representation."""
        discriminator_data = data.get("discriminator", {})
        discriminator = FactorDiscriminator(
            code=discriminator_data.get("code", ""),
            version=discriminator_data.get("version", "")
        )
        
        return cls(
            discriminator=discriminator,
            name=data.get("name"),
            group=data.get("group"),
            subgroup=data.get("subgroup"),
            source=data.get("source")
        )


@dataclass
class FactorDependency:
    """
    Represents a single factor dependency with its resolution requirements.
    
    Maps parameter names to factor references and includes resolution metadata.
    """
    parameter_name: str  # Key for calculate() method parameter
    factor_reference: FactorReference  # How to resolve this dependency
    required: bool = True  # Whether dependency is required for calculation
    default_value: Optional[Any] = None  # Default if optional and not resolved
    
    def __post_init__(self):
        if not self.parameter_name:
            raise ValueError("Parameter name is required for dependency")
        if not self.factor_reference:
            raise ValueError("Factor reference is required for dependency")


class FactorDependencyRegistry(ABC):
    """
    Abstract interface for resolving factor dependencies using discriminators.
    
    This registry maps discriminators to actual factor entities for dependency resolution.
    """
    
    @abstractmethod
    def register_factor(self, factor: Any, discriminator: FactorDiscriminator) -> None:
        """Register a factor with its discriminator."""
        pass
    
    @abstractmethod
    def resolve_factor(self, discriminator: FactorDiscriminator) -> Optional[Any]:
        """Resolve a factor by its discriminator."""
        pass
    
    @abstractmethod
    def list_registered_factors(self) -> List[FactorDiscriminator]:
        """List all registered factor discriminators."""
        pass


class InMemoryFactorDependencyRegistry(FactorDependencyRegistry):
    """
    In-memory implementation of factor dependency registry.
    
    Uses discriminator keys for fast lookup of factor entities.
    """
    
    def __init__(self):
        self._factor_map: Dict[str, Any] = {}
        self._discriminator_map: Dict[str, FactorDiscriminator] = {}
    
    def register_factor(self, factor: Any, discriminator: FactorDiscriminator) -> None:
        """Register a factor with its discriminator."""
        key = discriminator.to_key()
        self._factor_map[key] = factor
        self._discriminator_map[key] = discriminator
    
    def resolve_factor(self, discriminator: FactorDiscriminator) -> Optional[Any]:
        """Resolve a factor by its discriminator."""
        key = discriminator.to_key()
        return self._factor_map.get(key)
    
    def list_registered_factors(self) -> List[FactorDiscriminator]:
        """List all registered factor discriminators."""
        return list(self._discriminator_map.values())
    
    def get_factor_count(self) -> int:
        """Get count of registered factors."""
        return len(self._factor_map)


@dataclass
class FactorDependencyGraph:
    """
    Represents the complete dependency graph for a factor.
    
    Contains all dependencies and provides methods for validation and resolution.
    """
    dependencies: Dict[str, FactorDependency] = field(default_factory=dict)
    
    def add_dependency(self, dependency: FactorDependency) -> None:
        """Add a dependency to the graph."""
        self.dependencies[dependency.parameter_name] = dependency
    
    def get_dependency(self, parameter_name: str) -> Optional[FactorDependency]:
        """Get dependency by parameter name."""
        return self.dependencies.get(parameter_name)
    
    def get_required_dependencies(self) -> List[FactorDependency]:
        """Get all required dependencies."""
        return [dep for dep in self.dependencies.values() if dep.required]
    
    def get_optional_dependencies(self) -> List[FactorDependency]:
        """Get all optional dependencies."""
        return [dep for dep in self.dependencies.values() if not dep.required]
    
    def has_dependencies(self) -> bool:
        """Check if factor has any dependencies."""
        return len(self.dependencies) > 0
    
    def validate_dependency_names(self, parameter_names: List[str]) -> List[str]:
        """
        Validate that all required dependencies can be mapped to method parameters.
        
        Returns list of missing required dependencies.
        """
        missing = []
        for dep in self.get_required_dependencies():
            if dep.parameter_name not in parameter_names:
                missing.append(dep.parameter_name)
        return missing
    
    @classmethod
    def from_dependencies_dict(cls, dependencies_dict: Dict[str, Dict[str, Any]]) -> 'FactorDependencyGraph':
        """
        Create dependency graph from the dictionary format specified in the issue.
        
        Example input:
        {
            "spot_price": {
                "factor": {
                    "discriminator": {"code": "MARKET_SPOT_PRICE", "version": "v1"},
                    "name": "Spot Price",
                    "group": "Market Price",
                    "subgroup": "Spot",
                    "source": "IBKR"
                },
                "required": True
            }
        }
        """
        graph = cls()
        
        for param_name, dep_data in dependencies_dict.items():
            factor_data = dep_data.get("factor", {})
            factor_reference = FactorReference.from_dict(factor_data)
            
            dependency = FactorDependency(
                parameter_name=param_name,
                factor_reference=factor_reference,
                required=dep_data.get("required", True),
                default_value=dep_data.get("default_value")
            )
            
            graph.add_dependency(dependency)
        
        return graph
    
    def to_dependencies_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert back to the dictionary format for serialization."""
        result = {}
        
        for param_name, dependency in self.dependencies.items():
            result[param_name] = {
                "factor": dependency.factor_reference.to_dict(),
                "required": dependency.required
            }
            
            if dependency.default_value is not None:
                result[param_name]["default_value"] = dependency.default_value
        
        return result


class CyclicDependencyError(Exception):
    """Raised when a cyclic dependency is detected in the factor graph."""
    
    def __init__(self, cycle_path: List[str]):
        self.cycle_path = cycle_path
        super().__init__(f"Cyclic dependency detected: {' -> '.join(cycle_path)}")


class FactorDependencyValidator:
    """
    Validates factor dependency graphs for cycles and other structural issues.
    """
    
    def __init__(self, registry: FactorDependencyRegistry):
        self.registry = registry
    
    def validate_dag(self, starting_factors: List[Any]) -> None:
        """
        Validate that the dependency graph forms a DAG (no cycles).
        
        Args:
            starting_factors: List of factor entities to validate from
            
        Raises:
            CyclicDependencyError: If a cycle is detected
        """
        visited = set()
        rec_stack = set()
        
        for factor in starting_factors:
            if not self._has_cycle_dfs(factor, visited, rec_stack, []):
                continue
    
    def _has_cycle_dfs(self, factor: Any, visited: set, rec_stack: set, path: List[str]) -> bool:
        """
        DFS-based cycle detection.
        
        Returns True if cycle is found, False otherwise.
        """
        factor_id = str(getattr(factor, 'id', id(factor)))
        factor_name = getattr(factor, 'name', str(factor))
        
        if factor_id in rec_stack:
            # Cycle detected
            cycle_start_idx = path.index(factor_name) if factor_name in path else 0
            cycle_path = path[cycle_start_idx:] + [factor_name]
            raise CyclicDependencyError(cycle_path)
        
        if factor_id in visited:
            return False
        
        visited.add(factor_id)
        rec_stack.add(factor_id)
        current_path = path + [factor_name]
        
        # Get factor dependencies
        dependencies = self._get_factor_dependencies(factor)
        
        for dependency in dependencies.values():
            dep_factor = self.registry.resolve_factor(dependency.factor_reference.discriminator)
            if dep_factor and self._has_cycle_dfs(dep_factor, visited, rec_stack, current_path):
                return True
        
        rec_stack.remove(factor_id)
        return False
    
    def _get_factor_dependencies(self, factor: Any) -> Dict[str, FactorDependency]:
        """Get dependencies for a factor - to be implemented based on your factor structure."""
        dependencies = {}
        
        if hasattr(factor, 'dependencies'):
            deps_data = getattr(factor, 'dependencies')
            if isinstance(deps_data, dict):
                # Convert from class-level dependencies format
                graph = FactorDependencyGraph.from_dependencies_dict(deps_data)
                dependencies = graph.dependencies
        
        return dependencies