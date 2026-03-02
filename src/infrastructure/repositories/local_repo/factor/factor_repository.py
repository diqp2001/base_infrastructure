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
from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel


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
        # Search through nested libraries directly
        for library_key, library_value in FACTOR_LIBRARY.items():
            if isinstance(library_value, dict) and name in library_value:
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

    def get_factor_by_name_and_group(self, name: str, group: str) -> Optional[Factor]:
        """
        Retrieve a factor by both name and group parameters.
        
        Args:
            name: Factor name to search for
            group: Factor group to search for
            
        Returns:
            Factor entity or None if not found
        """
        try:
            model = self.session.query(FactorModel).filter(
                FactorModel.name == name,
                FactorModel.group == group
            ).first()
            return self._to_entity(model)
        except Exception as e:
            print(f"Error retrieving factor by name and group: {e}")
            return None

    def _populate_single_factor_dependencies(self, factor_name: str) -> int:
        """
        Populate dependencies for a single factor from FACTOR_LIBRARY configuration.
        
        Args:
            factor_name: Name of the factor to populate dependencies for
            
        Returns:
            Number of dependency relationships created
        """
        count = 0
        factor_config = self._get_factor_config_from_library(factor_name)
        
        if not factor_config:
            return count
            
        # Get or create the main factor
        main_factor = self.get_factor_by_name_and_group(factor_name, factor_config.get("group", "basic"))
        if not main_factor:
            main_factor = self._create_or_get_with_config(factor_name, factor_config)
            
        if not main_factor:
            return count
            
        # Handle structured dependencies (dict format with parameter names)
        dependencies = factor_config.get("dependencies", {})
        
        if isinstance(dependencies, dict):
            for param_name, dep_config in dependencies.items():
                if isinstance(dep_config, dict):
                    dep_name = dep_config.get("name")
                    dep_group = dep_config.get("group", "basic")
                    
                    # Get or create the dependency factor
                    dep_factor = self.get_factor_by_name_and_group(dep_name, dep_group)
                    if not dep_factor:
                        dep_factor = self._create_or_get_with_config(dep_name, dep_config)
                        
                    if dep_factor:
                        # Extract lag from parameters
                        lag = None
                        if "parameters" in dep_config and "lag" in dep_config["parameters"]:
                            lag = dep_config["parameters"]["lag"]
                            
                        # Check if dependency relationship already exists
                        existing_dep = self.session.query(FactorDependencyModel).filter(
                            FactorDependencyModel.dependent_factor_id == main_factor.id,
                            FactorDependencyModel.independent_factor_id == dep_factor.id,
                            FactorDependencyModel.lag == lag
                        ).first()
                        
                        if not existing_dep:
                            # Create new dependency relationship
                            dependency_model = FactorDependencyModel(
                                dependent_factor_id=main_factor.id,
                                independent_factor_id=dep_factor.id,
                                lag=lag
                            )
                            self.session.add(dependency_model)
                            count += 1
                            
        return count

    def populate_dependencies_from_library(self, factor_name: str = None) -> int:
        """
        Populate factor dependencies from FACTOR_LIBRARY configuration to database.
        
        Args:
            factor_name: Specific factor name to populate (None for all factors)
            
        Returns:
            Total number of dependency relationships created
        """
        total_count = 0
        
        try:
            if factor_name:
                # Populate dependencies for a specific factor
                total_count = self._populate_single_factor_dependencies(factor_name)
                print(f"Populated {total_count} dependencies for factor: {factor_name}")
            else:
                # Populate dependencies for all factors in library
                for library_name, library_content in FACTOR_LIBRARY.items():
                    if isinstance(library_content, dict):
                        for name, config in library_content.items():
                            if isinstance(config, dict) and "dependencies" in config:
                                count = self._populate_single_factor_dependencies(name)
                                total_count += count
                                if count > 0:
                                    print(f"Populated {count} dependencies for factor: {name}")
                                
            self.session.commit()
            
        except Exception as e:
            print(f"Error populating dependencies from library: {e}")
            self.session.rollback()
            
        return total_count

