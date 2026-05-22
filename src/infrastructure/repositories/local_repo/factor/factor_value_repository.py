# Factor Value Local Repository
# Mirrors src/infrastructure/models/factor/factor_value.py

import inspect
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.domain.entities.factor.factor_value import FactorValue
from src.infrastructure.models.factor.factor_value import FactorValueModel as FactorValueModel
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService


class FactorValueRepository(BaseLocalRepository, FactorValuePort):
    """Local repository for factor value model"""
    
    def __init__(self, session: Session, factory, mapper: FactorValueMapper = None):
        """Initialize FactorValueRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or FactorValueMapper()
        self._dependency_creation_stack = set()
        self.resolution_service = FactorValueResolutionService(factory=factory)
    
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
    
    def _create_or_get(self, entity_symbol, primary_key=None, **kwargs) -> Optional[FactorValue]:
        """
        Enhanced get_or_create function with automatic dependency resolution using FactorValueResolutionService.
        
        This method delegates to the resolution service for consistent dependency handling.
        
        Args:
            entity_symbol: Symbol identifier (for compatibility, not used in local version)
            primary_key: Optional primary key (not used in this implementation)
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
            
            if not financial_asset_entity:
                print("Financial asset entity is required for local factor value creation")
                return None
            
            # Use the resolution service to handle the factor value creation
            return self.resolution_service.resolve_factor_value(
                factor_entity=factor_entity,
                financial_asset_entity=financial_asset_entity,
                time_date=time_date,
                repository_type="local",
                **kwargs
            )
            
        except Exception as e:
            print(f"Error in _create_or_get for factor {factor_entity.name if factor_entity else 'unknown'}: {e}")
            return None

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
                    'dependency_entity': dependency,
                    'dependency_name': dependency.dependency_name
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
            if hasattr(factor, 'calculate') and callable(getattr(factor, 'calculate')):
                calculate_method = getattr(factor, 'calculate')

                # Get function signature
                signature = inspect.signature(calculate_method)

                # Parameter names
                parameter_names = list(signature.parameters.keys())
                for parameter in parameter_names:
                    dependency_values[parameter] = None  # Initialize with None


            for i, dependency in enumerate(dependencies):
                independent_factor_id = dependency['independent_factor_id']
                lag = dependency.get('lag')
                dependency_entity = dependency.get('dependency_entity')
                
                # Get the dependency name from the dependency entity
                dependency_name = getattr(dependency_entity, 'dependency_name', None) if dependency_entity else None
                
                # If no dependency name is specified, fall back to generic naming
                if not dependency_name:
                    dependency_name = f"factor_{independent_factor_id}_{lag}" if lag else f"factor_{independent_factor_id}"

                # Calculate dependency date with lag
                dependency_date = target_date
                if lag:
                    dependency_date = target_date - lag
                    while dependency_date.weekday() > 4:
                        dependency_date -= timedelta(days=1)
                
                dependency_date_str = dependency_date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Try to get existing dependency value from database
                dependency_value = self.get_by_factor_entity_date(
                    independent_factor_id, entity_id, dependency_date_str
                )
                
                if dependency_value:
                    # Use the dependency name as the key for the calculate method
                    dependency_values[dependency_name] = float(dependency_value.value)
                else:
                    print(f"Could not resolve dependency factor {independent_factor_id} ('{dependency_name}') for date {dependency_date_str}")
                    # Flag error instead of assigning 0.0
                    print(f"Local repository cannot resolve missing dependency - failing calculation")
                    return None
            
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
    def _get_dependency_parameter_name(self, factor: Any, dependency_index: int, total_dependencies: int, independent_factor: Any) -> str:
        """
        Get the parameter name for a dependency based on factor type and dependency position.
        
        Args:
            factor: The main factor requesting dependencies
            dependency_index: Index of this dependency in sorted list (0=highest lag, 1=lower lag, etc.)
            total_dependencies: Total number of dependencies
            independent_factor: The independent factor entity
            
        Returns:
            Parameter name to use for this dependency
        """
        try:
            factor_name = getattr(factor, 'name', '').lower()
            
            # For return factors with 2 dependencies, map to start_price/end_price
            if 'return' in factor_name and total_dependencies == 2:
                if dependency_index == 0:  # Highest lag = start_price
                    return 'start_price'
                elif dependency_index == 1:  # Lower lag = end_price
                    return 'end_price'
            
            # For other factors or different dependency counts, use factor name or generic names
            if total_dependencies == 1:
                return independent_factor.name
            else:
                # Multiple dependencies - use factor name with index
                return f"{independent_factor.name}_{dependency_index}"
            
        except Exception as e:
            print(f"Error determining parameter name: {e}")
            return independent_factor.name if independent_factor else f"param_{dependency_index}"

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
                    # Get function signature to determine how to call the method
                    signature = inspect.signature(calculate_method)
                    method_params = list(signature.parameters.keys())
                    
                    # Prepare arguments for the calculate method
                    call_kwargs = {}
                    for param_name in method_params:
                        if param_name in dependency_values:
                            call_kwargs[param_name] = dependency_values[param_name]
                    
                    # Add any additional kwargs that match method parameters
                    for key, value in kwargs.items():
                        if key in method_params:
                            call_kwargs[key] = value
                    
                    # Call the calculate method with the prepared arguments
                    result = calculate_method(**call_kwargs)
                    
                    if result is not None:
                        return float(result)
                    else:
                        print(f"Calculate method returned None for factor {factor.name}")
                        return None
                        
                except Exception as calc_error:
                    print(f"Error calling calculate method for factor {factor.name}: {calc_error}")
                    print(f"Available dependencies: {list(dependency_values.keys())}")
                    print(f"Method signature: {signature}")
                    return None
            else:
                print(f"Factor {factor.name} has dependencies but no calculate method")
                # Default calculation: sum of dependency values
                if dependency_values:
                    return sum(dependency_values.values())
                # Flag error instead of returning 0.0
                print(f"No dependency values available for calculation")
                return None
                
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
    
    def get_or_create_batch(self, factor_batch, **kwargs):
        """
        Batch get or create factor values using FactorValueResolutionService.
        
        Args:
            factor_batch: FactorBatch DTO containing factors to process
            **kwargs: Additional parameters for batch processing
            
        Returns:
            FactorValueBatch with resolved factor values or None if failed
        """
        try:
            if not factor_batch or factor_batch.is_empty():
                print("Cannot process empty factor batch")
                return None
            
            print(f"Processing batch with {len(factor_batch.factors)} factors via resolution service")
            return self.resolution_service.resolve_factor_values_batch(
                factor_batch=factor_batch,
                repository_type="local",
                **kwargs
            )
            
        except Exception as e:
            print(f"Error in local repository batch processing: {e}")
            return None
    
    def get_or_create_batch_optimized(self, entities_data, **kwargs):
        """
        Optimized batch method for EntityService integration.
        
        Args:
            entities_data: List of dictionaries containing entity data for batch processing
            **kwargs: Additional parameters for batch processing
            
        Returns:
            List of resolved FactorValue entities
        """
        try:
            if not entities_data:
                print("Cannot process empty entities_data")
                return []
            
            print(f"Processing optimized batch with {len(entities_data)} entities via resolution service")
            return self.resolution_service.resolve_factor_values_optimized_batch(
                entities_data=entities_data,
                repository_type="local",
                **kwargs
            )
            
        except Exception as e:
            print(f"Error in local repository optimized batch processing: {e}")
            return []