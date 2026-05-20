# Factor Value Local Repository
# Mirrors src/infrastructure/models/factor/factor_value.py

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.models.factor.factor_value import FactorValueModel as FactorValueModel
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper


class FactorValueRepository(BaseLocalRepository, FactorValuePort):
    """Local repository for factor value model"""
    
    def __init__(self, session: Session, factory, mapper: FactorValueMapper = None):
        """Initialize FactorValueRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FactorValueMapper()
        self._dependency_creation_stack = set()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return FactorValueModel
    @property
    def entity_class(self):
        """Return the SQLAlchemy model class for FactorValue."""
        return FactorValue
    
    def _to_entity(self, model: FactorValueModel) -> FactorValue:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: FactorValue) -> FactorValueModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
            
    
    def get_by_id(self, entity_id: int) -> Optional[FactorValue]:
        """Get factor value by ID."""
        model = self.session.query(FactorValueModel).filter(
            FactorValueModel.id == entity_id
        ).first()
        return self._to_entity(model)
    
    def get_by_name(self, name: str) -> Optional[FactorValue]:
        """Get factor value by name (not applicable for factor values)."""
        # Factor values don't have names, return None
        return None
    
    def get_by_group(self, group: str) -> List[FactorValue]:
        """Get factor values by group (not applicable for factor values)."""
        # Factor values don't have groups, return empty list
        return []
    
    def get_by_subgroup(self, subgroup: str) -> List[FactorValue]:
        """Get factor values by subgroup (not applicable for factor values)."""
        # Factor values don't have subgroups, return empty list
        return []
    
    def get_all(self) -> List[FactorValue]:
        """Get all factor values."""
        models = self.session.query(FactorValueModel).all()
        return [self._to_entity(model) for model in models]
    
    def add(self, entity: FactorValue) -> Optional[FactorValue]:
        """Add/persist a factor value entity."""
        try:
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            return self._to_entity(model)
        except Exception as e:
            print(f"Error adding factor value: {e}")
            self.session.rollback()
            return None
    
    def update(self, entity: FactorValue) -> Optional[FactorValue]:
        """Update a factor value entity."""
        try:
            model = self.session.query(FactorValueModel).filter(
                FactorValueModel.id == entity.id
            ).first()
            
            if not model:
                return None
            
            model.factor_id = entity.factor_id
            model.entity_id = entity.entity_id
            model.date = entity.date
            model.value = entity.value
            
            self.session.commit()
            return self._to_entity(model)
        except Exception as e:
            print(f"Error updating factor value: {e}")
            self.session.rollback()
            return None
    
    def delete(self, entity_id: int) -> bool:
        """Delete a factor value entity."""
        try:
            model = self.session.query(FactorValueModel).filter(
                FactorValueModel.id == entity_id
            ).first()
            
            if not model:
                return False
            
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting factor value: {e}")
            self.session.rollback()
            return False
    
    def get_all_dates_by_id_entity_id(self, factor_id: int, entity_id: int) -> List[str]:
        """Get all dates for a specific factor and entity combination."""
        try:
            dates = self.session.query(FactorValueModel.date).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id
            ).all()
            
            return [str(date_tuple[0]) for date_tuple in dates]
        except Exception as e:
            print(f"Error getting dates for factor {factor_id} and entity {entity_id}: {e}")
            return []
    
    def get_by_factor_entity_date(self, factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]:
        """Get factor value by factor ID, entity ID, and date."""
        try:
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            
            model = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date == date_obj
            ).first()
            
            return self._to_entity(model)
        except Exception as e:
            print(f"Error getting factor value for factor {factor_id}, entity {entity_id}, date {date_str}: {e}")
            return None
    
    def _create_or_get(self, entity_symbol, **kwargs) -> Optional[FactorValue]:
        """
        Enhanced get_or_create function with automatic dependency resolution and local database integration.
        
        This method implements factor value creation with dependency handling:
        1. Takes factor entity, financial asset entity, date, and kwargs
        2. If no dependencies: creates factor value directly from provided value or default
        3. If dependencies: resolves other factor values from database, uses calculate function
        4. Stores the result in the database
        
        Args:
            entity_symbol: Symbol identifier (for compatibility, not used in local version)
            **kwargs: Parameters including:
                - factor: Factor domain entity instance
                - entity: Financial asset entity 
                - date: Date string in 'YYYY-MM-DD HH:MM:SS' format
                - value: Optional explicit value to use
                
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            factor_entity = kwargs.get('factor')
            financial_asset_entity = kwargs.get('entity')
            time_date = kwargs.get('date', datetime.now())
            
            if not factor_entity:
                print("Factor entity is required for local factor value creation")
                return None

            # Get entity ID safely
            entity_id = getattr(financial_asset_entity, 'id') if financial_asset_entity else None
            if not entity_id:
                print("Financial asset entity with valid ID is required")
                return None

            # Check for dependency loop protection
            dependency_key = (factor_entity.id, entity_id, str(time_date))
            if dependency_key in self._dependency_creation_stack:
                print(f"Detected dependency loop for factor {factor_entity.name} with entity {entity_id}. Skipping to prevent infinite recursion.")
                return None
                
            # Add to dependency stack for loop protection
            self._dependency_creation_stack.add(dependency_key)

            try:
                # Ensure time_date is a string
                if isinstance(time_date, date):
                    time_date = time_date.strftime("%Y-%m-%d %H:%M:%S")
                elif not isinstance(time_date, str):
                    time_date = str(time_date)

                # Check if factor value already exists
                existing = self.get_by_factor_entity_date(factor_entity.id, entity_id, time_date)
                if existing:
                    return existing

                # Parse date object for storage
                target_date = datetime.strptime(time_date, "%Y-%m-%d %H:%M:%S")

                # Get factor dependencies from the database
                dependencies = self._get_factor_dependencies_from_db(factor_entity.id)

                if dependencies:
                    # Factor has dependencies - use calculate function
                    print(f"Factor {factor_entity.name} has {len(dependencies)} dependencies - using calculate function")
                    print(f"Using static dependency resolution for factor {factor_entity.name}")
                    
                    factor_value = self._handle_factor_with_dependencies(
                        factor_entity, dependencies, entity_id, target_date, **kwargs
                    )
                    return factor_value
                    
                else:
                    # Factor has no dependencies - create directly from provided value or default
                    print(f"Factor {factor_entity.name} has no dependencies - using local database")
                    
                    # Use provided value or default to 0.0
                    factor_value_data = kwargs.get('value', '0.0')
                    
                    # Create new factor value entity
                    factor_value = FactorValue(
                        id=None,  # Let database auto-increment handle ID generation
                        factor_id=factor_entity.id,
                        entity_id=entity_id,
                        date=target_date,
                        value=str(factor_value_data)
                    )
                    
                    # Persist to database
                    created_value = self.add(factor_value)
                    if created_value:
                        print(f"Created factor value: {factor_entity.name} = {factor_value.value}")
                        return created_value
                
                print(f"Failed to create factor value for factor {factor_entity.name}")
                return None
                    
            except Exception as e:
                print(f"Error in _create_or_get for factor {factor_entity.name}: {e}")
                self.session.rollback()
                return None
                
        finally:
            # Clean up dependency stack to prevent memory leaks
            if 'dependency_key' in locals() and dependency_key in self._dependency_creation_stack:
                self._dependency_creation_stack.remove(dependency_key)

    def _get_factor_dependencies_from_db(self, factor_id: int) -> List[Dict[str, Any]]:
        """
        Get factor dependencies from database.
        
        Args:
            factor_id: ID of the factor to check for dependencies
            
        Returns:
            List of dependency information dictionaries
        """
        try:
            # Get factor dependency repository from factory
            if not self.factory:
                return []
                
            factor_dependency_repo = getattr(self.factory, 'factor_dependency_local_repo', None)
            if not factor_dependency_repo:
                print(f"Factor dependency repository not found in factory")
                return []
            
            # Get dependencies where this factor is the dependent factor
            dependencies = factor_dependency_repo.get_by_dependent_factor_id(factor_id)
            
            if not dependencies:
                return []
            
            # Convert to dictionary format expected by calculation logic
            dependency_list = []
            for dependency in dependencies:
                dependency_info = {
                    'independent_factor_id': dependency.independent_factor_id,
                    'dependent_factor_id': dependency.dependent_factor_id,
                    'lag': dependency.lag,
                    'dependency_entity': dependency
                }
                dependency_list.append(dependency_info)
            
            return dependency_list
            
        except Exception as e:
            print(f"Error getting dependencies for factor {factor_id}: {e}")
            return []

    def _handle_factor_with_dependencies(self, factor: Any, dependencies: List[Dict[str, Any]], 
                                       entity_id: int, target_date: datetime, **kwargs) -> Optional[FactorValue]:
        """
        Handle factor calculation when factor has dependencies.
        
        Args:
            factor: Factor entity with dependencies
            dependencies: List of dependency information
            entity_id: Entity ID for the factor value
            target_date: Date for the factor value
            **kwargs: Additional parameters for calculation
            
        Returns:
            Calculated FactorValue or None if calculation failed
        """
        try:
            # Resolve dependency factor values from local database
            dependency_values = {}
            
            for dependency in dependencies:
                independent_factor_id = dependency['independent_factor_id']
                lag = dependency.get('lag')
                
                # Calculate dependency date with lag
                dependency_date = target_date
                if lag:
                    dependency_date = target_date - lag
                
                dependency_date_str = dependency_date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Try to get existing dependency value from database
                dependency_value = self.get_by_factor_entity_date(
                    independent_factor_id, entity_id, dependency_date_str
                )
                
                if dependency_value:
                    # Use the factor name as key if available
                    dependency_key = f"factor_{independent_factor_id}"
                    dependency_values[dependency_key] = float(dependency_value.value)
                else:
                    print(f"Could not resolve dependency factor {independent_factor_id} for date {dependency_date_str}")
                    # Set default value for missing dependencies
                    dependency_key = f"factor_{independent_factor_id}"
                    dependency_values[dependency_key] = 0.0
            
            # Call the factor's calculate method if it exists
            calculated_value = self._call_factor_calculate_method(factor, dependency_values, **kwargs)
            
            if calculated_value is not None:
                # Create new factor value entity with calculated result
                factor_value = FactorValue(
                    id=None,
                    factor_id=factor.id,
                    entity_id=entity_id,
                    date=target_date,
                    value=str(calculated_value)
                )
                
                # Persist to database
                created_value = self.add(factor_value)
                if created_value:
                    print(f"Created calculated factor value: {factor.name} = {calculated_value}")
                    return created_value
            
            print(f"Failed to calculate factor value for factor {factor.name}")
            return None
            
        except Exception as e:
            print(f"Error handling factor with dependencies {factor.name}: {e}")
            return None

    def _call_factor_calculate_method(self, factor: Any, dependency_values: Dict[str, float], **kwargs) -> Optional[float]:
        """
        Call the factor's calculate method to compute the factor value.
        
        Args:
            factor: Factor entity with calculate method
            dependency_values: Dictionary of resolved dependency values
            **kwargs: Additional parameters for calculation
            
        Returns:
            Calculated factor value or None if calculation failed
        """
        try:
            # Look for calculate method in the factor
            if hasattr(factor, 'calculate') and callable(getattr(factor, 'calculate')):
                calculate_method = getattr(factor, 'calculate')
                
                try:
                    # Call the calculate method with dependency values
                    result = calculate_method(dependency_values, **kwargs)
                    
                    if result is not None:
                        return float(result)
                    else:
                        print(f"Calculate method returned None for factor {factor.name}")
                        return None
                        
                except Exception as calc_error:
                    print(f"Error calling calculate method for factor {factor.name}: {calc_error}")
                    return None
            else:
                print(f"Factor {factor.name} has dependencies but no calculate method")
                # Default calculation: sum of dependency values
                if dependency_values:
                    return sum(dependency_values.values())
                return 0.0
                
        except Exception as e:
            print(f"Error in factor calculation for {factor.name}: {e}")
            return None

    def _create_or_get_legacy(self, factor_id: int, entity_id: int, date: date, value: str) -> Optional[FactorValue]:
        """Legacy create or get method for backward compatibility."""
        # Check if entity already exists by factor_id, entity_id, and date
        existing = self.get_by_factor_entity_date(factor_id, entity_id, str(date))
        if existing:
            return existing
        
        try:
            # Create new factor value entity without manual ID assignment
            # Let the database auto-increment handle ID generation
            factor_value = FactorValue(
                id=None,  # Let database auto-increment handle ID generation
                factor_id=factor_id,
                entity_id=entity_id,
                date=date,
                value=value
            )
            
            # Add to database
            return self.add(factor_value)
            
        except Exception as e:
            print(f"Error creating factor value for factor {factor_id}, entity {entity_id}: {str(e)}")
            return None

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[FactorValue]:
        """
        Get or create a factor value with dependency resolution.
        
        Args:
            primary_key: Composite key "factor_id_entity_id_date"
            **kwargs: Additional parameters for factor value creation
            
        Returns:
            FactorValue entity or None if creation failed
        """
        try:
            # Parse composite primary key - expecting format "factor_id_entity_id_date"
            parts = primary_key.split('_', 2)
            if len(parts) != 3:
                print(f"Invalid primary key format: {primary_key}. Expected format: 'factor_id_entity_id_date'")
                return None
                
            factor_id = int(parts[0])
            entity_id = int(parts[1])
            date_str = parts[2]
            
            # Check existing by composite key
            existing = self.get_by_factor_entity_date(factor_id, entity_id, date_str)
            if existing:
                return existing
            
            # Create new factor value using legacy create_or_get method for backward compatibility
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            
            return self._create_or_get_legacy(
                factor_id=factor_id,
                entity_id=entity_id,
                date=date_obj,
                value=kwargs.get('value', '0.0')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for factor value {primary_key}: {e}")
            return None