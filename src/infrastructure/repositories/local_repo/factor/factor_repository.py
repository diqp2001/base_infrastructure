# Factor Local Repository
# Mirrors src/infrastructure/models/factor/factor.py

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.factor import Factor
from src.infrastructure.models.factor.factor import FactorModel as FactorModel
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.domain.ports.factor.factor_port import FactorPort
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.application.services.data.entities.factor.factor_library.factor_definition_config import get_factor_config, FACTOR_LIBRARY


class FactorRepository(BaseFactorRepository, FactorPort):

    def __init__(self, session: Session, factory, mapper: FactorMapper = None, entity_factor_class_input = None, factor_dependency_repository = None):
        """Initialize FactorRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FactorMapper()
        self.factor_dependency_repository = factor_dependency_repository
        

    # ----------------------------
    # Required by BaseLocalRepository
    # ----------------------------
    def redef_entity_class(self,entity_factor_class_input = None):
        self.entity_class_input =entity_factor_class_input
    @property
    def model_class(self):
        return FactorModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Factor."""
        if self.entity_class_input== None:
            return Factor
        
        return self.entity_class_input

    def _to_entity(self, model: FactorModel) -> Optional[Factor]:
        if not model:
            return None
        return self.mapper.to_domain(model)

    def _to_model(self, entity: Factor) -> FactorModel:
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    def _get_factor_config_from_library(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find factor configuration from the factor library by name.
        Searches through all nested libraries (INDEX_LIBRARY, FUTURE_INDEX_LIBRARY, etc.)
        """
        # Check main FACTOR_LIBRARY first
        config = get_factor_config(name)
        if config:
            return config
            
        # Search through nested libraries
        for library_key, library_value in FACTOR_LIBRARY.items():
            if isinstance(library_value, set) and len(library_value) == 1:
                # Handle the current nested structure like {"future_index_library":{FUTURE_INDEX_LIBRARY}}
                nested_lib = list(library_value)[0]
                if isinstance(nested_lib, dict) and name in nested_lib:
                    return nested_lib[name]
            elif isinstance(library_value, dict) and name in library_value:
                return library_value[name]
                
        return None

    def _create_or_get_dependencies(self, factor_config: Dict[str, Any]) -> List[Factor]:
        """
        Recursively create or get dependencies for a factor.
        Handles both list-style and dict-style dependencies.
        """
        dependencies = factor_config.get("dependencies", [])
        created_dependencies = []
        
        if isinstance(dependencies, list):
            # Handle list-style dependencies: ["close", "open"]
            for dep_name in dependencies:
                dep_config = self._get_factor_config_from_library(dep_name)
                if dep_config:
                    dep_factor = self._create_or_get_with_config(dep_name, dep_config)
                    if dep_factor:
                        created_dependencies.append(dep_factor)
                else:
                    # Create basic factor if no config found
                    dep_factor = self._create_or_get(dep_name, "basic", "unknown")
                    if dep_factor:
                        created_dependencies.append(dep_factor)
        
        elif isinstance(dependencies, dict):
            # Handle dict-style dependencies: {"open": {...}}
            for dep_name, dep_config in dependencies.items():
                if isinstance(dep_config, dict):
                    dep_factor = self._create_or_get_with_config(dep_name, dep_config)
                    if dep_factor:
                        created_dependencies.append(dep_factor)
        
        return created_dependencies

    def _establish_dependencies(self, main_factor: Factor, dependencies: List[Factor]) -> None:
        """
        Establish dependency relationships in the database using FactorDependencyRepository.
        """
        if not self.factor_dependency_repository:
            return
            
        for dep_factor in dependencies:
            try:
                # Check if dependency relationship already exists
                if not self.factor_dependency_repository.exists(main_factor.id, dep_factor.id):
                    dependency = FactorDependency(
                        dependent_factor_id=main_factor.id,
                        independent_factor_id=dep_factor.id
                    )
                    self.factor_dependency_repository.add(dependency)
            except Exception as e:
                print(f"Warning: Could not establish dependency between {main_factor.name} and {dep_factor.name}: {e}")

    def _create_or_get_with_config(self, name: str, factor_config: Dict[str, Any]) -> Factor:
        """
        Create or get a factor using its configuration from the factor library.
        Handles dependencies recursively.
        """
        # Extract config values with defaults
        group = factor_config.get("group", "basic")
        subgroup = factor_config.get("subgroup", "unknown")
        
        # Check if factor already exists
        existing = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.group == group,
            FactorModel.subgroup == subgroup
        ).first()

        if existing:
            return self._to_entity(existing)

        # Create dependencies first
        dependencies = self._create_or_get_dependencies(factor_config)
        
        # Create the main factor
        entity_class = factor_config.get("class", self.entity_class)
        entity = entity_class(
            id=self._get_next_available_id(),
            name=name,
            group=group,
            subgroup=subgroup
        )

        created_factor = self.create(entity)
        
        # Establish dependency relationships
        if created_factor and dependencies:
            self._establish_dependencies(created_factor, dependencies)
        
        return created_factor

    def _create_or_get(self, name: str, group: str, subgroup: str) -> Factor:
        """
        Create or get a factor. Now enhanced to handle dependencies if factor config is found.
        """
        # First try to get factor config from library
        factor_config = self._get_factor_config_from_library(name)
        
        if factor_config:
            # Use config-based creation with dependency handling
            return self._create_or_get_with_config(name, factor_config)
        
        # Fallback to original simple creation for factors not in library
        existing = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.group == group,
            FactorModel.subgroup == subgroup
        ).first()

        if existing:
            return self._to_entity(existing)

        entity = self.entity_class(
            id=self._get_next_available_id(),
            name=name,
            group=group,
            subgroup=subgroup
        )

        return self.create(entity)

    # ----------------------------
    # Required by FactorPort
    # ----------------------------

    def get_by_id(self, factor_id: int) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.id == factor_id
        ).first()
        return self._to_entity(model)

    def get_by_name(self, name: str) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.name == name
        ).first()
        return self._to_entity(model)
    def get_by_name_and_factor_type(self, name: str, factor_type: str) -> Optional[Factor]:
        model = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.factor_type == factor_type
        ).first()
        return self._to_entity(model)

    def get_by_group(self, group: str) -> List[Factor]:
        models = self.session.query(FactorModel).filter(
            FactorModel.group == group
        ).all()
        return [self._to_entity(m) for m in models]

    def get_by_subgroup(self, subgroup: str) -> List[Factor]:
        models = self.session.query(FactorModel).filter(
            FactorModel.subgroup == subgroup
        ).all()
        return [self._to_entity(m) for m in models]

    def get_factor_by_name_and_group(self, name: str, group: str) -> Optional[Factor]:
        """
        Get factor by name and group.
        
        Args:
            name: Factor name
            group: Factor group
            
        Returns:
            Factor entity if found, None otherwise
        """
        model = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.group == group
        ).first()
        return self._to_entity(model)

    def populate_dependencies_from_library(self, factor_name: str = None) -> int:
        """
        Populate factor dependencies from FACTOR_LIBRARY configuration to database.
        
        Args:
            factor_name: If provided, only populate dependencies for this specific factor.
                        If None, populate all factors from library.
                        
        Returns:
            Number of dependency relationships created
        """
        created_count = 0
        
        if factor_name:
            # Populate dependencies for specific factor
            factor_config = self._get_factor_config_from_library(factor_name)
            if factor_config:
                created_count += self._populate_single_factor_dependencies(factor_name, factor_config)
        else:
            # Populate all factors from library
            created_count += self._populate_all_library_dependencies()
            
        return created_count

    def _populate_single_factor_dependencies(self, factor_name: str, factor_config: Dict[str, Any]) -> int:
        """
        Populate dependencies for a single factor from its configuration.
        
        Args:
            factor_name: Name of the factor
            factor_config: Configuration dictionary from factor library
            
        Returns:
            Number of dependency relationships created for this factor
        """
        created_count = 0
        
        # Get or create the main factor
        main_factor = self._create_or_get_with_config(factor_name, factor_config)
        if not main_factor:
            return 0
            
        dependencies = factor_config.get("dependencies", {})
        
        if isinstance(dependencies, dict):
            # Handle structured dependencies like {"start_price": {...}, "end_price": {...}}
            for dep_param_name, dep_config in dependencies.items():
                if isinstance(dep_config, dict):
                    dep_name = dep_config.get("name", dep_param_name)
                    dep_group = dep_config.get("group", "basic")
                    
                    # Get or create dependency factor
                    dep_factor = self._create_or_get_with_config(dep_name, dep_config)
                    if dep_factor and self.factor_dependency_repository:
                        
                        # Extract lag information
                        lag_timedelta = None
                        parameters = dep_config.get("parameters", {})
                        if "lag" in parameters:
                            lag_timedelta = parameters["lag"]
                            
                        # Create dependency relationship
                        if not self.factor_dependency_repository.exists(main_factor.id, dep_factor.id):
                            from src.domain.entities.factor.factor_dependency import FactorDependency
                            dependency = FactorDependency(
                                dependent_factor_id=main_factor.id,
                                independent_factor_id=dep_factor.id,
                                lag=lag_timedelta
                            )
                            self.factor_dependency_repository.add(dependency)
                            created_count += 1
                            
        elif isinstance(dependencies, list):
            # Handle simple list dependencies like ["close", "open"]
            for dep_name in dependencies:
                dep_config = self._get_factor_config_from_library(dep_name)
                if dep_config:
                    dep_factor = self._create_or_get_with_config(dep_name, dep_config)
                else:
                    dep_factor = self._create_or_get(dep_name, "basic", "unknown")
                    
                if dep_factor and self.factor_dependency_repository:
                    if not self.factor_dependency_repository.exists(main_factor.id, dep_factor.id):
                        from src.domain.entities.factor.factor_dependency import FactorDependency
                        dependency = FactorDependency(
                            dependent_factor_id=main_factor.id,
                            independent_factor_id=dep_factor.id
                        )
                        self.factor_dependency_repository.add(dependency)
                        created_count += 1
                        
        return created_count

    def _populate_all_library_dependencies(self) -> int:
        """
        Populate dependencies for all factors in the FACTOR_LIBRARY.
        
        Returns:
            Total number of dependency relationships created
        """
        created_count = 0
        
        # Traverse all nested libraries in FACTOR_LIBRARY
        for library_key, library_value in FACTOR_LIBRARY.items():
            if isinstance(library_value, dict):
                # Direct dictionary of factors
                for factor_name, factor_config in library_value.items():
                    if isinstance(factor_config, dict):
                        created_count += self._populate_single_factor_dependencies(factor_name, factor_config)
            elif isinstance(library_value, set) and len(library_value) == 1:
                # Handle nested structure like {"future_index_library":{FUTURE_INDEX_LIBRARY}}
                nested_lib = list(library_value)[0]
                if isinstance(nested_lib, dict):
                    for factor_name, factor_config in nested_lib.items():
                        if isinstance(factor_config, dict):
                            created_count += self._populate_single_factor_dependencies(factor_name, factor_config)
                            
        return created_count

    def create_factor_with_dependencies(self, name: str) -> Optional[Factor]:
        """
        Public method to create a factor with all its dependencies from the factor library.
        
        Args:
            name: Factor name to create
            
        Returns:
            Created Factor entity with dependencies, or None if not found in library
        """
        factor_config = self._get_factor_config_from_library(name)
        if not factor_config:
            return None
            
        return self._create_or_get_with_config(name, factor_config)

