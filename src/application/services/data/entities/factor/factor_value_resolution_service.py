"""
Factor Value Resolution Service

This service provides dependency resolution capabilities for factor value calculation.
It handles both direct dependencies (option -> underlying asset) and indirect dependencies 
(portfolio -> holdings) as described in issue #551.

Supports both local repository and IBKR repository integration.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, date, timedelta
import logging
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue
from src.dto.factor.factor_batch import FactorBatch
from src.dto.factor.factor_value_batch import FactorValueBatch


class FactorValueResolutionService:
    """
    Service for resolving factor value dependencies and orchestrating calculations.
    
    Handles both:
    1. Direct dependencies: Entity contains reference to related entity (e.g., option -> underlying_asset_id)
    2. Indirect dependencies: Related entities reference the current entity (e.g., holdings -> portfolio_id)
    """
    
    def __init__(self, factory=None, logger=None):
        """
        Initialize the resolution service.
        
        Args:
            factory: Repository factory for accessing different repositories
            logger: Optional logger for debugging
        """
        self.factory = factory
        self.logger = logger or logging.getLogger(__name__)
        self._dependency_creation_stack: Set[Tuple[int, int, str]] = set()
    
    def resolve_factor_value(
        self,
        factor_entity,
        financial_asset_entity,
        time_date,
        repository_type: str = "local",
        **kwargs
    ) -> Optional[FactorValue]:
        """
        Main method to resolve factor value with dependency handling.
        
        Args:
            factor_entity: Factor domain entity instance
            financial_asset_entity: Financial asset entity
            time_date: Date for factor value calculation
            repository_type: "local" or "ibkr" for repository selection
            **kwargs: Additional parameters for calculation
            
        Returns:
            FactorValue entity or None if resolution failed
        """
        try:
            if not factor_entity or not factor_entity.id:
                self.logger.error("Factor entity is required for factor value resolution")
                return None
            
            # Get entity ID safely
            entity_id = getattr(financial_asset_entity, 'id') if financial_asset_entity else None
            if not entity_id:
                self.logger.error("Financial asset entity with valid ID is required")
                return None
            
            # Check for dependency loop protection
            dependency_key = (factor_entity.id, entity_id, str(time_date))
            if dependency_key in self._dependency_creation_stack:
                self.logger.warning(f"Detected dependency loop for factor {factor_entity.name} with entity {entity_id}")
                return None
            
            # Add to dependency stack for loop protection
            self._dependency_creation_stack.add(dependency_key)
            
            try:
                # Ensure time_date is properly formatted
                formatted_date = self._format_date(time_date)
                parsed_date = self._parse_date(formatted_date)
                
                # Check if factor value already exists
                existing_value = self._check_existing_value(
                    factor_entity.id, entity_id, formatted_date, repository_type
                )
                if existing_value:
                    return existing_value
                
                # Get factor dependencies
                dependencies = self._get_factor_dependencies(factor_entity.id)
                
                if dependencies:
                    # Factor has dependencies - resolve them and calculate
                    self.logger.info(f"Factor {factor_entity.name} has {len(dependencies)} dependencies")
                    return self._resolve_factor_with_dependencies(
                        factor_entity, dependencies, entity_id, parsed_date, 
                        repository_type, **kwargs
                    )
                else:
                    # Factor has no dependencies - create directly
                    self.logger.info(f"Factor {factor_entity.name} has no dependencies")
                    return self._resolve_factor_without_dependencies(
                        factor_entity, entity_id, parsed_date, repository_type, **kwargs
                    )
                    
            finally:
                # Clean up dependency stack
                if dependency_key in self._dependency_creation_stack:
                    self._dependency_creation_stack.remove(dependency_key)
                    
        except Exception as e:
            self.logger.error(f"Error resolving factor value for {factor_entity.name}: {e}")
            return None
    
    def resolve_aggregated_factor_value(
        self,
        factor_entity,
        parent_entity,
        time_date,
        aggregation_strategy: str = "sum",
        repository_type: str = "local",
        **kwargs
    ) -> Optional[FactorValue]:
        """
        Resolve factor value that requires aggregation from related entities.
        
        This handles indirect dependencies like portfolio value = sum of holding values.
        
        Args:
            factor_entity: Factor requiring aggregation (e.g., PortfolioValueFactor)
            parent_entity: Parent entity (e.g., Portfolio)
            time_date: Date for calculation
            aggregation_strategy: "sum", "average", "max", "min"
            repository_type: "local" or "ibkr"
            **kwargs: Additional parameters
            
        Returns:
            FactorValue with aggregated result
        """
        try:
            # Get related entities (e.g., holdings for a portfolio)
            related_entities = self._get_related_entities(parent_entity, repository_type)
            
            if not related_entities:
                self.logger.error(f"No related entities found for {parent_entity} - cannot calculate aggregated value")
                # Flag error instead of returning zero value
                return None
            
            # Resolve factor values for each related entity
            dependency_values = {}
            failed_entities = []
            
            for i, related_entity in enumerate(related_entities):
                # For aggregation, we use the same factor for each related entity
                related_factor_value = self.resolve_factor_value(
                    factor_entity, related_entity, time_date, repository_type, **kwargs
                )
                
                if related_factor_value:
                    key = f"factor_{factor_entity.id}_{i}"
                    dependency_values[key] = self._convert_to_float(related_factor_value.value)
                else:
                    failed_entities.append(related_entity.id)
                    self.logger.error(f"Could not resolve factor value for related entity {related_entity.id}")
            
            # If any related entities failed, flag error instead of partial aggregation
            if failed_entities:
                self.logger.error(f"Cannot calculate aggregated factor {factor_entity.name} - failed entities: {failed_entities}")
                return None
            
            # Ensure we have values to aggregate
            if not dependency_values:
                self.logger.error(f"No valid factor values found for aggregation of {factor_entity.name}")
                return None
            
            # Apply aggregation strategy
            aggregated_value = self._apply_aggregation_strategy(dependency_values, aggregation_strategy)
            
            # Create and persist the aggregated factor value
            return self._create_factor_value(
                factor_entity, parent_entity.id, time_date, str(aggregated_value), repository_type
            )
            
        except Exception as e:
            self.logger.error(f"Error resolving aggregated factor value: {e}")
            return None
    
    def _format_date(self, time_date) -> str:
        """Format date to string format."""
        if isinstance(time_date, date):
            return time_date.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(time_date, str):
            return time_date
        else:
            return str(time_date)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Try alternative format
            return datetime.strptime(date_str, "%Y-%m-%d")
    
    def _check_existing_value(
        self, factor_id: int, entity_id: int, date_str: str, repository_type: str
    ) -> Optional[FactorValue]:
        """Check if factor value already exists in the repository."""
        try:
            if repository_type == "local":
                repo = getattr(self.factory, 'factor_value_local_repo', None)
            else:
                repo = getattr(self.factory, 'factor_value_ibkr_repo', None)
            
            if repo and hasattr(repo, 'get_by_factor_entity_date'):
                return repo.get_by_factor_entity_date(factor_id, entity_id, date_str)
            
            return None
        except Exception as e:
            self.logger.error(f"Error checking existing value: {e}")
            return None
    
    def _get_factor_dependencies(self, factor_id: int) -> List[Dict[str, Any]]:
        """Get factor dependencies from database."""
        try:
            if not self.factory:
                return []
            
            factor_dependency_repo = getattr(self.factory, 'factor_dependency_local_repo', None)
            if not factor_dependency_repo:
                self.logger.warning("Factor dependency repository not found")
                return []
            
            dependencies = factor_dependency_repo.get_by_dependent_factor_id(factor_id)
            
            if not dependencies:
                return []
            
            # Convert to dictionary format
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
            self.logger.error(f"Error getting dependencies for factor {factor_id}: {e}")
            return []
    
    def _resolve_factor_with_dependencies(
        self,
        factor_entity,
        dependencies: List[Dict[str, Any]],
        entity_id: int,
        target_date: datetime,
        repository_type: str,
        **kwargs
    ) -> Optional[FactorValue]:
        """Resolve factor value when dependencies exist."""
        try:
            dependency_values = {}
            missing_dependencies = []
            
            for dependency in dependencies:
                independent_factor_id = dependency['independent_factor_id']
                lag = dependency.get('lag')
                dependency_name = dependency.get('dependency_name')
                
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
                
                # Get dependency value from repository
                dependency_value = self._check_existing_value(
                    independent_factor_id, entity_id, dependency_date_str, repository_type
                )
                
                if dependency_value:
                    dependency_values[dependency_name] = self._convert_to_float(dependency_value.value)
                else:
                    # Handle missing dependencies based on repository type
                    dependency_resolved = self._handle_missing_dependency(
                        independent_factor_id, entity_id, dependency_date_str, repository_type
                    )
                    
                    if dependency_resolved:
                        dependency_values[dependency_name] = self._convert_to_float(dependency_resolved.value)
                    else:
                        missing_dependencies.append(dependency["dependency_entity"])
                        self.logger.error(f"Failed to resolve dependency factor {independent_factor_id} ('{dependency_name}') for {repository_type} repository")
            
            # If there are missing dependencies, flag error and do not assign 0
            if missing_dependencies:
                self.logger.error(f"Cannot calculate factor {factor_entity.name} - missing dependencies: {missing_dependencies}")
                return None
            
            # Calculate using factor's calculate method
            calculated_value = self._call_factor_calculate_method(factor_entity, dependency_values, **kwargs)
            
            if calculated_value is not None:
                return self._create_factor_value(
                    factor_entity, entity_id, target_date, str(calculated_value), repository_type
                )
            
            self.logger.error(f"Factor calculation failed for {factor_entity.name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error resolving factor with dependencies: {e}")
            return None
    
    def _handle_missing_dependency(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str,
        repository_type: str
    ) -> Optional[FactorValue]:
        """
        Handle missing dependency values based on repository type.
        
        Args:
            factor_id: ID of the missing dependency factor
            entity_id: Entity ID for the dependency
            date_str: Date string for the dependency
            repository_type: "local" or "ibkr" for repository-specific handling
            
        Returns:
            FactorValue if resolved, None if failed (never returns 0)
        """
        try:
            if repository_type == "local":
                # Local repo strategy: Flag error, don't assign 0
                self.logger.error(f"Local repository cannot resolve missing dependency factor {factor_id}")
                return None
                
            elif repository_type == "ibkr":
                # IBKR repo strategy: Try to fetch from IBKR, then flag error if not found
                self.logger.info(f"Attempting to fetch missing dependency factor {factor_id} from IBKR")
                
                # Get the IBKR repository
                ibkr_repo = getattr(self.factory, 'factor_value_ibkr_repo', None)
                if not ibkr_repo:
                    self.logger.error("IBKR repository not available for dependency resolution")
                    return None
                
                # Get the factor entity
                factor_repo = getattr(self.factory, 'factor_local_repo', None)
                if not factor_repo:
                    self.logger.error("Factor repository not available")
                    return None
                
                factor_entity = factor_repo.get_by_id(factor_id)
                if not factor_entity:
                    self.logger.error(f"Factor entity {factor_id} not found")
                    return None
                
                # Get financial asset entity
                financial_asset_entity = getattr(self.factory, 'financial_asset_local_repo', None)
                if not financial_asset_entity:
                    self.logger.error("Financial asset repository not available")
                    return None
                
                financial_asset_entity = financial_asset_entity.get_by_id(entity_id)
                if not financial_asset_entity:
                    self.logger.error(f"Financial asset entity {entity_id} not found")
                    return None
                
                # Try to fetch from IBKR using the IBKR-specific method
                if hasattr(ibkr_repo, '_fetch_factor_value_from_ibkr'):
                    fetched_value = ibkr_repo._fetch_factor_value_from_ibkr(
                        factor_entity=factor_entity,
                        financial_asset_entity=financial_asset_entity,
                        time_date=date_str,
                        entity_symbol=getattr(financial_asset_entity, 'symbol', '')
                    )
                    
                    if fetched_value:
                        self.logger.info(f"Successfully fetched dependency factor {factor_id} from IBKR")
                        return fetched_value
                
                # If IBKR fetch failed, flag error
                self.logger.error(f"IBKR repository could not fetch dependency factor {factor_id}")
                return None
            
            else:
                self.logger.error(f"Unknown repository type: {repository_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error handling missing dependency: {e}")
            return None
    
    def _resolve_factor_without_dependencies(
        self,
        factor_entity,
        entity_id: int,
        target_date: datetime,
        repository_type: str,
        **kwargs
    ) -> Optional[FactorValue]:
        """Resolve factor value when no dependencies exist."""
        try:
            # Handle non-dependent factors based on repository type
            if repository_type == "local":
                # Local repo: Only create if explicit value provided, otherwise flag error
                factor_value_data = kwargs.get('value')
                if factor_value_data is None:
                    self.logger.error(f"Local repository requires explicit value for factor {factor_entity.name}")
                    return None
                
                return self._create_factor_value(
                    factor_entity, entity_id, target_date, str(factor_value_data), repository_type
                )
                
            elif repository_type == "ibkr":
                # IBKR repo: Try to fetch from IBKR first
                ibkr_repo = getattr(self.factory, 'factor_value_ibkr_repo', None)
                if ibkr_repo and hasattr(ibkr_repo, '_fetch_factor_value_from_ibkr'):
                    # Get financial asset entity
                    financial_asset_entity = getattr(self.factory, 'financial_asset_local_repo', None)
                    if financial_asset_entity:
                        financial_asset_entity = financial_asset_entity.get_by_id(entity_id)
                        if financial_asset_entity:
                            fetched_value = ibkr_repo._fetch_factor_value_from_ibkr(
                                factor_entity=factor_entity,
                                financial_asset_entity=financial_asset_entity,
                                time_date=target_date,
                                entity_symbol=getattr(financial_asset_entity, 'symbol', ''),
                                **kwargs
                            )
                            
                            if fetched_value:
                                return fetched_value
                
                # If IBKR fetch failed, flag error
                self.logger.error(f"IBKR repository could not fetch factor {factor_entity.name}")
                return None
            
            else:
                self.logger.error(f"Unknown repository type: {repository_type}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error resolving factor without dependencies: {e}")
            return None
    
    def _get_related_entities(self, parent_entity, repository_type: str) -> List[Any]:
        """
        Get entities that are related to the parent entity.
        
        For example: Get all holdings for a portfolio.
        """
        try:
            # This is a placeholder - actual implementation depends on entity relationships
            # For portfolio -> holdings relationship:
            if hasattr(parent_entity, '__class__') and 'Portfolio' in parent_entity.__class__.__name__:
                if repository_type == "local":
                    holding_repo = getattr(self.factory, 'holding_local_repo', None)
                else:
                    holding_repo = getattr(self.factory, 'holding_ibkr_repo', None)
                
                if holding_repo and hasattr(holding_repo, 'get_by_portfolio_id'):
                    return holding_repo.get_by_portfolio_id(parent_entity.id)
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting related entities: {e}")
            return []
    
    def _apply_aggregation_strategy(
        self, dependency_values: Dict[str, float], strategy: str
    ) -> float:
        """Apply aggregation strategy to dependency values."""
        
        
        values = list(dependency_values.values())
        
        if strategy == "sum":
            return sum(values)
        elif strategy == "average":
            return sum(values) / len(values)
        elif strategy == "max":
            return max(values)
        elif strategy == "min":
            return min(values)
        else:
            self.logger.warning(f"Unknown aggregation strategy: {strategy}, using sum")
            return sum(values)
    
    def _call_factor_calculate_method(
        self, factor_entity, dependency_values: Dict[str, float], **kwargs
    ) -> Optional[float]:
        """Call the factor's calculate method."""
        try:
            if hasattr(factor_entity, 'calculate') and callable(getattr(factor_entity, 'calculate')):
                calculate_method = getattr(factor_entity, 'calculate')
                
                # Get function signature to determine how to call the method
                import inspect
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
                    self.logger.warning(f"Calculate method returned None for factor {factor_entity.name}")
                    return None
            else:
                self.logger.error(f"Factor {factor_entity.name} does not have a calculate method")
                return None
                
                
        except Exception as e:
            self.logger.error(f"Error calling factor calculate method: {e}")
            self.logger.error(f"Available dependencies: {list(dependency_values.keys())}")
            self.logger.error(f"Factor: {factor_entity.name}")
            return None
    
    def _create_factor_value(
        self,
        factor_entity,
        entity_id: int,
        target_date: datetime,
        value: str,
        repository_type: str
    ) -> Optional[FactorValue]:
        """Create and persist factor value to repository."""
        try:
            # Create factor value entity
            factor_value = FactorValue(
                id=None,  # Let database auto-increment handle ID
                factor_id=factor_entity.id,
                entity_id=entity_id,
                date=target_date,
                value=value
            )
            
            # Get appropriate repository and persist
            if repository_type == "local":
                repo = getattr(self.factory, 'factor_value_local_repo', None)
            else:
                repo = getattr(self.factory, 'factor_value_ibkr_repo', None)
            
            if repo and hasattr(repo, 'add'):
                created_value = repo.add(factor_value)
                if created_value:
                    self.logger.info(f"Created factor value: {factor_entity.name} = {value}")
                    return created_value
            
            self.logger.error(f"Could not persist factor value for {factor_entity.name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating factor value: {e}")
            return None
    
    def _convert_to_float(self, value) -> float:
        """Convert various numeric types to float."""
        try:
            if isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, str):
                return float(value)
            elif isinstance(value, (int, float)):
                return float(value)
            else:
                self.logger.warning(f"Unknown value type for conversion: {type(value)}")
                
        except (ValueError, TypeError):
            self.logger.error(f"Error converting value to float: {value}")
            
    
    def resolve_factor_values_batch(
        self,
        factor_batch: FactorBatch,
        repository_type: str = "local",
        **kwargs
    ) -> Optional[FactorValueBatch]:
        """
        Batch resolution of factor values with dependency handling.
        
        This method processes multiple factors efficiently while maintaining
        dependency resolution capabilities for each factor.
        
        Args:
            factor_batch: FactorBatch DTO containing factors to process
            repository_type: "local" or "ibkr" for repository selection
            **kwargs: Additional parameters for batch processing
            
        Returns:
            FactorValueBatch with resolved factor values or None if failed
        """
        try:
            if factor_batch.is_empty():
                self.logger.warning("Cannot process empty factor batch")
                return None
            
            # Extract metadata
            financial_asset_entity = factor_batch.metadata.get('financial_asset_entity')
            time_date = factor_batch.metadata.get('time_date', datetime.now())
            
            # Convert time to datetime if needed
            if isinstance(time_date, str):
                time_date = datetime.strptime(time_date, "%Y-%m-%d %H:%M:%S")
            
            resolved_factor_values = []
            failed_resolutions = []
            
            # Process each entity_id in the batch
            for entity_id in factor_batch.entity_ids:
                # Process each factor for the current entity
                for factor in factor_batch.factors:
                    try:
                        # Use the single factor resolution method for each factor
                        factor_value = self.resolve_factor_value(
                            factor_entity=factor,
                            financial_asset_entity=financial_asset_entity,
                            time_date=time_date,
                            repository_type=repository_type,
                            **kwargs
                        )
                        
                        if factor_value:
                            resolved_factor_values.append(factor_value)
                        else:
                            # Follow repository-specific error handling - no default values
                            failed_resolutions.append({
                                'factor_id': factor.id,
                                'factor_name': factor.name,
                                'entity_id': entity_id,
                                'reason': f'Factor value resolution failed for {repository_type} repository'
                            })
                            self.logger.error(f"Failed to resolve factor {factor.name} for entity {entity_id} in {repository_type} repository")
                    
                    except Exception as factor_error:
                        self.logger.error(f"Error resolving factor {factor.name} for entity {entity_id}: {factor_error}")
                        failed_resolutions.append({
                            'factor_id': factor.id,
                            'factor_name': factor.name,
                            'entity_id': entity_id,
                            'reason': str(factor_error)
                        })
            
            # Create result metadata
            result_metadata = {
                'processed_count': len(resolved_factor_values),
                'failed_count': len(failed_resolutions),
                'original_batch_size': len(factor_batch.factors) * len(factor_batch.entity_ids),
                'processing_timestamp': datetime.now().isoformat(),
                'failed_resolutions': failed_resolutions
            }
            
            if not resolved_factor_values:
                self.logger.warning("No factor values were successfully resolved from batch")
                return FactorValueBatch(
                    factor_values=[],
                    metadata=result_metadata
                )
            
            self.logger.info(f"Successfully resolved {len(resolved_factor_values)} factor values from batch")
            
            return FactorValueBatch(
                factor_values=resolved_factor_values,
                metadata=result_metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error in batch factor value resolution: {e}")
            return None
        finally:
            # Clear dependency stack after batch processing
            self._dependency_creation_stack.clear()
    
    def resolve_factor_values_optimized_batch(
        self,
        entities_data: List[Dict[str, Any]],
        repository_type: str = "local",
        **kwargs
    ) -> List[FactorValue]:
        """
        Optimized batch resolution for EntityService integration.
        
        This method provides an optimized interface for processing multiple
        entities with their associated factors efficiently.
        
        Args:
            entities_data: List of dictionaries containing entity data for batch processing
                Expected format: [{'factor': Factor, 'entity_id': int, 'financial_asset_entity': Entity, ...}, ...]
            repository_type: "local" or "ibkr" for repository selection  
            **kwargs: Additional parameters for batch processing
            
        Returns:
            List of resolved FactorValue entities
        """
        try:
            if not entities_data:
                self.logger.warning("Cannot process empty entities_data")
                return []
            
            resolved_factor_values = []
            
            # Group entities by asset class for optimized processing
            entities_by_asset_class = {}
            for entity_data in entities_data:
                financial_asset_entity = entity_data.get('financial_asset_entity')
                if financial_asset_entity:
                    asset_class = type(financial_asset_entity)
                    if asset_class not in entities_by_asset_class:
                        entities_by_asset_class[asset_class] = []
                    entities_by_asset_class[asset_class].append(entity_data)
            
            # Process each asset class group
            for asset_class, asset_entities in entities_by_asset_class.items():
                try:
                    # Extract factors and entity IDs for this asset class
                    factors = []
                    entity_ids = set()
                    sample_entity = None
                    time_date = datetime.now()
                    
                    for entity_data in asset_entities:
                        factor = entity_data.get('factor')
                        if factor:
                            factors.append(factor)
                        
                        entity_id = entity_data.get('entity_id')
                        if entity_id:
                            entity_ids.add(entity_id)
                        
                        if not sample_entity:
                            sample_entity = entity_data.get('financial_asset_entity')
                        
                        if 'time_date' in entity_data:
                            time_date = entity_data['time_date']
                    
                    if factors and entity_ids and sample_entity:
                        # Create FactorBatch for this asset class
                        batch_metadata = {
                            'financial_asset_entity': sample_entity,
                            'time_date': time_date,
                            'asset_class': asset_class.__name__
                        }
                        
                        factor_batch = FactorBatch(
                            factors=factors,
                            entity_ids=list(entity_ids),
                            metadata=batch_metadata
                        )
                        
                        # Process the batch
                        batch_result = self.resolve_factor_values_batch(
                            factor_batch=factor_batch,
                            repository_type=repository_type,
                            **kwargs
                        )
                        
                        if batch_result and batch_result.factor_values:
                            resolved_factor_values.extend(batch_result.factor_values)
                
                except Exception as asset_class_error:
                    self.logger.error(f"Error processing asset class {asset_class.__name__}: {asset_class_error}")
                    continue
            
            self.logger.info(f"Optimized batch resolved {len(resolved_factor_values)} factor values")
            return resolved_factor_values
            
        except Exception as e:
            self.logger.error(f"Error in optimized batch resolution: {e}")
            return []
        finally:
            # Clear dependency stack after batch processing
            self._dependency_creation_stack.clear()