"""
Factor Value Resolution Service

This service provides dependency resolution capabilities for factor value calculation.
It handles both direct dependencies (option -> underlying asset) and indirect dependencies 
(portfolio -> holdings) as described in issue #551.

Supports both local repository and IBKR repository integration.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, date, timedelta
import inspect
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
        entity,
        time_date,
        repository_type: str = "local",
        # Backward-compat alias kept so existing callers still work
        financial_asset_entity=None,
        **kwargs
    ) -> Optional[FactorValue]:
        """
        Main method to resolve factor value with dependency handling.

        Args:
            factor_entity: Factor domain entity instance
            entity: The domain Entity for which the factor value is computed.
                    Accepts any Entity subclass (Country, CompanyShare, Portfolio, …).
                    The ``financial_asset_entity`` keyword is kept as a deprecated
                    alias and is used as a fallback when ``entity`` is None.
            time_date: Date for factor value calculation
            repository_type: "local" or "ibkr" for repository selection
            **kwargs: Additional parameters for calculation

        Returns:
            FactorValue entity or None if resolution failed
        """
        # Support deprecated keyword alias
        if entity is None and financial_asset_entity is not None:
            entity = financial_asset_entity

        try:
            if not factor_entity or not factor_entity.id:
                self.logger.error("Factor entity is required for factor value resolution")
                return None

            # Get entity ID safely
            entity_id = getattr(entity, 'id', None) if entity is not None else None
            if not entity_id:
                self.logger.error("Entity with valid ID is required for factor value resolution")
                return None

            entity_type = type(entity).__name__ if entity is not None else None

            # Check for dependency loop protection
            dependency_key = (factor_entity.id, entity_id, entity_type, str(time_date))
            if dependency_key in self._dependency_creation_stack:
                self.logger.warning(
                    f"Detected dependency loop for factor {factor_entity.name} "
                    f"with entity {entity_type}:{entity_id}"
                )
                return None

            # Add to dependency stack for loop protection
            self._dependency_creation_stack.add(dependency_key)

            try:
                # Ensure time_date is properly formatted
                formatted_date = self._format_date(time_date)
                parsed_date = self._parse_date(formatted_date)

                # Check if factor value already exists
                existing_value = self._check_existing_value(
                    factor_entity.id, entity_id, entity_type, formatted_date, repository_type
                )
                if existing_value:
                    return existing_value

                # Get factor dependencies from database
                dependencies = self._get_factor_dependencies(factor_entity.id)

                # Check if factor has calculate function (indicates dynamic dependencies)
                has_calculate_function = hasattr(factor_entity, 'calculate') and callable(getattr(factor_entity, 'calculate'))

                if dependencies or has_calculate_function:
                    # Factor has dependencies (database or dynamic) - resolve them and calculate
                    if dependencies:
                        self.logger.info(f"Factor {factor_entity.name} has {len(dependencies)} database dependencies")
                    if has_calculate_function and not dependencies:
                        self.logger.info(f"Factor {factor_entity.name} has dynamic dependencies (calculate function)")
                    
                    return self._resolve_factor_with_dependencies(
                        factor_entity, dependencies, entity, parsed_date,
                        repository_type, has_calculate_function, **kwargs
                    )
                else:
                    # Factor has no dependencies - create directly
                    self.logger.info(f"Factor {factor_entity.name} has no dependencies")
                    return self._resolve_factor_without_dependencies(
                        factor_entity, entity, parsed_date, repository_type, **kwargs
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
                    factor_entity=factor_entity,
                    entity=related_entity,
                    time_date=time_date,
                    repository_type=repository_type,
                    **kwargs
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
        self,
        factor_id: int,
        entity_id: int,
        entity_type: Optional[str],
        date_str: str,
        repository_type: str,
    ) -> Optional[FactorValue]:
        """Check if factor value already exists in the repository."""
        try:
            if repository_type == "local":
                repo = getattr(self.factory, 'factor_value_local_repo', None)
            else:
                repo = getattr(self.factory, 'factor_value_ibkr_repo', None)

            if repo and hasattr(repo, 'get_by_factor_entity_date'):
                return repo.get_by_factor_entity_date(factor_id, entity_id, date_str, entity_type=entity_type)

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
        entity,
        target_date: datetime,
        repository_type: str,
        has_calculate_function: bool = False,
        **kwargs
    ) -> Optional[FactorValue]:
        """Resolve factor value when dependencies exist."""
        try:
            entity_id = getattr(entity, 'id', None) if entity is not None else None
            entity_type = type(entity).__name__ if entity is not None else None

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
                    independent_factor_id, entity_id, entity_type, dependency_date_str, repository_type
                )

                if dependency_value:
                    dependency_values[dependency_name] = self._convert_to_float(dependency_value.value)
                else:
                    # Handle missing dependencies based on repository type
                    dependency_resolved = self._handle_missing_dependency(
                        independent_factor_id, entity, dependency_date_str, repository_type
                    )

                    if dependency_resolved:
                        dependency_values[dependency_name] = self._convert_to_float(dependency_resolved.value)
                    else:
                        missing_dependencies.append(dependency["dependency_entity"])
                        self.logger.error(
                            f"Failed to resolve dependency factor {independent_factor_id} "
                            f"('{dependency_name}') for {repository_type} repository"
                        )

            # Handle dynamic dependencies if factor has calculate function
            if has_calculate_function and not dependencies:
                # Factor has calculate function but no database dependencies - resolve dynamic dependencies
                dynamic_dependency_values = self._resolve_dynamic_dependencies(
                    factor_entity, entity, target_date, repository_type, **kwargs
                )
                if dynamic_dependency_values:
                    dependency_values.update(dynamic_dependency_values)
                else:
                    self.logger.error(f"Failed to resolve dynamic dependencies for factor {factor_entity.name}")
                    return None

            # If there are missing dependencies (and no dynamic dependencies resolved them), flag error
            if missing_dependencies and not (has_calculate_function and dependency_values):
                self.logger.error(
                    f"Cannot calculate factor {factor_entity.name} - missing dependencies: {missing_dependencies}"
                )
                return None

            # Calculate using factor's calculate method
            calculated_value = self._call_factor_calculate_method(factor_entity, dependency_values, **kwargs)

            if calculated_value is not None:
                return self._create_factor_value(
                    factor_entity, entity, target_date, str(calculated_value), repository_type
                )

            self.logger.error(f"Factor calculation failed for {factor_entity.name}")
            return None

        except Exception as e:
            self.logger.error(f"Error resolving factor with dependencies: {e}")
            return None
    
    def _handle_missing_dependency(
        self,
        factor_id: int,
        entity,
        date_str: str,
        repository_type: str,
    ) -> Optional[FactorValue]:
        """
        Handle missing dependency values based on repository type.

        Args:
            factor_id: ID of the missing dependency factor
            entity: The domain Entity (any Entity subclass) for the dependency
            date_str: Date string for the dependency
            repository_type: "local" or "ibkr" for repository-specific handling

        Returns:
            FactorValue if resolved, None if failed (never returns 0)
        """
        try:
            entity_id = getattr(entity, 'id', None) if entity is not None else None

            if repository_type == "local":
                # Before failing, try to aggregate from related entities
                # (e.g., holding_value for each holding → sum → portfolio_value dependency)
                related_entities = self._get_related_entities(entity, repository_type)

                if related_entities:
                    # Fetch the dependency factor entity so we can call resolve_factor_value
                    factor_repo = getattr(self.factory, 'factor_local_repo', None)
                    if not factor_repo:
                        self.logger.error(
                            "Factor repository not available for aggregation of dependency "
                            f"factor {factor_id}"
                        )
                        return None

                    dep_factor_entity = factor_repo.get_by_id(factor_id)
                    if not dep_factor_entity:
                        self.logger.error(
                            f"Factor entity {factor_id} not found; cannot aggregate"
                        )
                        return None

                    # Resolve the dependency for every related entity and sum the results
                    aggregated_total = 0.0
                    failed_related = []

                    for related_entity in related_entities:
                        # Holding-type entities need specialised treatment:
                        # their value = asset_price × position_quantity.
                        # The price lives as a FactorValue on holding.asset (not on the
                        # holding itself), and quantity lives on holding.position /
                        # transactions / orders – never as a FactorValue.
                        if 'Holding' in type(related_entity).__name__:
                            related_value = self._resolve_holding_value_factor(
                                dep_factor_entity, related_entity, date_str, repository_type
                            )
                        else:
                            related_value = self.resolve_factor_value(
                                factor_entity=dep_factor_entity,
                                entity=related_entity,
                                time_date=date_str,
                                repository_type=repository_type,
                            )
                        if related_value is not None:
                            aggregated_total += self._convert_to_float(related_value.value)
                        else:
                            failed_related.append(
                                getattr(related_entity, 'id', repr(related_entity))
                            )

                    if failed_related:
                        self.logger.error(
                            f"Cannot aggregate dependency factor {factor_id}: "
                            f"failed for related entity ids {failed_related}"
                        )
                        return None

                    # Return a transient FactorValue carrying the aggregated result.
                    # It is NOT persisted here – the caller (_resolve_factor_with_dependencies)
                    # only reads .value from it to feed into the parent factor's calculate().
                    parsed_date = self._parse_date(date_str)
                    return FactorValue(
                        id=None,
                        factor_id=factor_id,
                        entity=entity,
                        date=parsed_date,
                        value=str(aggregated_total),
                    )

                # No related entities – local repo cannot resolve this dependency
                self.logger.error(
                    f"Local repository cannot resolve missing dependency factor {factor_id}"
                )
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

                # Try to fetch from IBKR using the IBKR-specific method
                if hasattr(ibkr_repo, '_fetch_factor_value_from_ibkr'):
                    fetched_value = ibkr_repo._fetch_factor_value_from_ibkr(
                        factor_entity=factor_entity,
                        entity=entity,
                        time_date=date_str,
                        entity_symbol=getattr(entity, 'symbol', '')
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

    def _resolve_dynamic_dependencies(
        self,
        factor_entity,
        entity,
        target_date: datetime,
        repository_type: str,
        **kwargs
    ) -> Optional[Dict[str, float]]:
        """
        Resolve dynamic dependencies by finding related entities and their factor values.
        
        This method:
        1. Gets related entities (e.g., portfolio -> holdings)
        2. For each related entity, tries to get factor values for factors with matching parameters
        3. Returns a dictionary of dependency values for the calculate function
        
        Args:
            factor_entity: Factor that needs dynamic dependencies resolved
            entity: Parent entity (e.g., Portfolio)
            target_date: Date for calculation
            repository_type: "local" or "ibkr"
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of dependency values or None if resolution failed
        """
        try:
            entity_id = getattr(entity, 'id', None) if entity is not None else None
            if not entity_id:
                self.logger.error("Entity ID required for dynamic dependency resolution")
                return None

            # Get related entities using the get_related_entities method
            related_entities = self._get_related_entities(entity, repository_type)
            
            if not related_entities:
                self.logger.warning(f"No related entities found for {type(entity).__name__}:{entity_id}")
                return None

            self.logger.info(f"Found {len(related_entities)} related entities for dynamic dependency resolution")
            
            # Get all factors with matching parameters (frequency, group, subgroup, data_type)
            matching_factors = self._find_matching_factors(factor_entity, repository_type)
            
            dependency_values = {}
            
            # For each related entity, try to find factor values
            for i, related_entity in enumerate(related_entities):
                related_entity_id = getattr(related_entity, 'id', None)
                related_entity_type = type(related_entity).__name__
                
                if not related_entity_id:
                    continue
                    
                # Try to find factor values for this related entity
                for matching_factor in matching_factors:
                    factor_value = self._check_existing_value(
                        matching_factor.id, related_entity_id, related_entity_type, 
                        target_date.strftime("%Y-%m-%d %H:%M:%S"), repository_type
                    )
                    
                    if factor_value:
                        # Create a dependency name based on factor and related entity
                        dependency_name = f"{matching_factor.name}_{related_entity_type}_{i}"
                        dependency_values[dependency_name] = self._convert_to_float(factor_value.value)
                        self.logger.info(f"Found dynamic dependency: {dependency_name} = {factor_value.value}")
                        break
                
                # If no factor value found, try to resolve it recursively
                if not any(f"{mf.name}_{related_entity_type}_{i}" in dependency_values for mf in matching_factors):
                    for matching_factor in matching_factors:
                        resolved_value = self.resolve_factor_value(
                            factor_entity=matching_factor,
                            entity=related_entity,
                            time_date=target_date,
                            repository_type=repository_type,
                            **kwargs
                        )
                        
                        if resolved_value:
                            dependency_name = f"{matching_factor.name}_{related_entity_type}_{i}"
                            dependency_values[dependency_name] = self._convert_to_float(resolved_value.value)
                            self.logger.info(f"Resolved dynamic dependency: {dependency_name} = {resolved_value.value}")
                            break
            
            if dependency_values:
                self.logger.info(f"Successfully resolved {len(dependency_values)} dynamic dependencies")
                return dependency_values
            else:
                self.logger.warning("No dynamic dependencies could be resolved")
                return None
                
        except Exception as e:
            self.logger.error(f"Error resolving dynamic dependencies: {e}")
            return None

    def _find_matching_factors(self, factor_entity, repository_type: str) -> List[Any]:
        """
        Find factors with matching parameters (frequency, group, subgroup, data_type).
        
        Args:
            factor_entity: Source factor to match parameters against
            repository_type: "local" or "ibkr"
            
        Returns:
            List of matching factor entities
        """
        try:
            if repository_type == "local":
                factor_repo = getattr(self.factory, 'factor_local_repo', None)
            else:
                factor_repo = getattr(self.factory, 'factor_ibkr_repo', None)
                
            if not factor_repo or not hasattr(factor_repo, 'get_all'):
                self.logger.warning("Factor repository not available for matching factors")
                return []
                
            # Get all factors
            all_factors = factor_repo.get_all() or []
            
            # Filter factors with matching parameters
            matching_factors = []
            for factor in all_factors:
                if (factor.frequency == factor_entity.frequency and
                    factor.group == factor_entity.group and
                    factor.subgroup == factor_entity.subgroup and
                    factor.data_type == factor_entity.data_type):
                    matching_factors.append(factor)
                    
            self.logger.info(f"Found {len(matching_factors)} factors matching parameters")
            return matching_factors
            
        except Exception as e:
            self.logger.error(f"Error finding matching factors: {e}")
            return []
    
    def _resolve_factor_without_dependencies(
        self,
        factor_entity,
        entity,
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
                    factor_entity, entity, target_date, str(factor_value_data), repository_type
                )

            elif repository_type == "ibkr":
                # IBKR repo: Try to fetch from IBKR first
                ibkr_repo = getattr(self.factory, 'factor_value_ibkr_repo', None)
                if ibkr_repo and hasattr(ibkr_repo, '_fetch_factor_value_from_ibkr'):
                    if entity is not None:
                        fetched_value = ibkr_repo._fetch_factor_value_from_ibkr(
                            factor_entity=factor_entity,
                            entity=entity,
                            time_date=target_date,
                            entity_symbol=getattr(entity, 'symbol', ''),
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
    
    # ------------------------------------------------------------------
    # Holding-value specialised helpers
    # ------------------------------------------------------------------

    def _resolve_holding_value_factor(
        self,
        dep_factor_entity,
        holding,
        date_str: str,
        repository_type: str,
    ) -> Optional[FactorValue]:
        """
        Compute and persist a holding-value FactorValue for one holding entity.

        Formula: holding_value = asset_price × position_quantity

        * asset_price  → FactorValue stored for ``holding.asset`` (e.g. CompanyShare
                          close price), resolved via the dep_factor_entity's DB
                          dependencies OR by a name-based fallback search.
        * quantity     → ``holding.position.quantity`` directly, or looked up from
                         the Position / Transaction / Order repos (they carry the
                         quantity directly – it is never stored as a FactorValue).

        If a FactorValue already exists in the DB for this holding it is returned
        immediately without recomputing.
        """
        holding_id   = getattr(holding, 'id', None)
        holding_type = type(holding).__name__

        # 1. Return existing stored value if present
        existing = self._check_existing_value(
            dep_factor_entity.id, holding_id, holding_type, date_str, repository_type
        )
        if existing:
            return existing

        # 2. Get the underlying financial asset (e.g. CompanyShare)
        asset = getattr(holding, 'asset', None)
        if asset is None:
            self.logger.error(
                f"Holding {holding_id} ({holding_type}) has no 'asset' attribute; "
                "cannot compute holding_value"
            )
            return None

        # 3. Get quantity
        quantity = self._get_holding_quantity(holding, date_str, repository_type)
        if quantity is None:
            self.logger.error(
                f"Could not determine quantity for holding {holding_id} ({holding_type})"
            )
            return None

        # 4. Get asset price at date
        price = self._get_asset_price_for_holding_value(
            asset, dep_factor_entity, date_str, repository_type
        )
        if price is None:
            # Asset might be a sub-portfolio (e.g. CompanySharePortfolioPortfolioHolding)
            # rather than a directly-priced instrument.  Try to resolve it as a portfolio
            # and aggregate its own holdings' values recursively.
            asset_id = getattr(asset, 'id', None)
            sub_portfolio = self._try_get_sub_portfolio(asset_id)
            if sub_portfolio is not None:
                return self._aggregate_sub_portfolio_holding_value(
                    dep_factor_entity, sub_portfolio, date_str, repository_type
                )
            self.logger.error(
                f"Could not find price factor value for asset {getattr(asset, 'id', '?')} "
                f"({type(asset).__name__}) at {date_str}"
            )
            return None

        # 5. Compute value
        position = getattr(holding, 'position', None)

        if hasattr(dep_factor_entity, 'calculate'):
            sig    = inspect.signature(dep_factor_entity.calculate)
            params = list(sig.parameters.keys())
            if 'dependencies' in params:
                # dict-based calculate: resolve the price-key name from the factor's
                # own DB dependencies so any holding type works (share, currency,
                # bond, portfolio, …) — no hardcoded key.
                price_key = self._get_price_dependency_name(dep_factor_entity)
                result = dep_factor_entity.calculate({
                    price_key: price,
                    'position': position if position is not None else quantity,
                })
            else:
                result = Decimal(str(price)) * Decimal(str(quantity))
        else:
            result = Decimal(str(price)) * Decimal(str(quantity))

        # 6. Persist and return
        parsed_date = self._parse_date(date_str)
        return self._create_factor_value(
            dep_factor_entity, holding, parsed_date, str(result), repository_type
        )

    def _get_price_dependency_name(self, factor_entity) -> str:
        """
        Return the key name expected for the price/value dependency in
        factor_entity.calculate(dependencies).

        Reads the factor's own dependency rows from the DB and returns the
        dependency_name of the first row that is not 'position'.  Falls back
        to 'price' when nothing is found so the caller always gets a usable key.
        """
        factor_dep_repo = getattr(self.factory, 'factor_dependency_local_repo', None)
        if factor_dep_repo and getattr(factor_entity, 'id', None):
            try:
                deps = factor_dep_repo.get_by_dependent_factor_id(factor_entity.id) or []
                for dep in deps:
                    name = getattr(dep, 'dependency_name', None)
                    if name and name != 'position':
                        return name
            except Exception as e:
                self.logger.debug(f"Could not resolve price dependency name: {e}")
        return 'price'

    def _get_holding_quantity(
        self,
        holding,
        date_str: str,
        repository_type: str,
    ) -> Optional[float]:
        """
        Return the share quantity for a holding.

        Priority order:
          1. ``holding.position.quantity``  (cheapest – already in memory)
          2. Position repo  ``get_by_portfolio_id``  filtered by asset_id
          3. Transaction repo  ``get_by_portfolio_id``  (sum of matched transactions)
          4. Order repo  ``get_by_portfolio_id``        (sum of matched orders)
        """
        # 1. In-memory position — only trust if quantity is explicitly non-zero.
        # HoldingMapper creates a dummy Position(quantity=0), so a zero here means
        # "not set by the mapper" and we should fall through to the DB.
        position = getattr(holding, 'position', None)
        if position is not None:
            qty = getattr(position, 'quantity', None)
            if qty is not None and qty != 0:
                return float(qty)

        asset_id     = getattr(getattr(holding, 'asset', None), 'id', None)
        container    = getattr(holding, 'container', None)
        container_id = getattr(container, 'id', None)

        prefix = 'local' if repository_type == 'local' else 'ibkr'

        # 2. Position repo
        if container_id:
            pos_repo = getattr(self.factory, f'position_{prefix}_repo', None)
            if pos_repo and hasattr(pos_repo, 'get_by_portfolio_id'):
                positions = pos_repo.get_by_portfolio_id(container_id) or []
                for pos in positions:
                    if asset_id and getattr(pos, 'asset_id', None) == asset_id:
                        return float(getattr(pos, 'quantity', 0))
                if positions:
                    # No asset-id match – fall back to first position quantity
                    return float(getattr(positions[0], 'quantity', 0))

        # 3. Transaction repo (sum of fills for this asset)
        if container_id:
            tx_repo = getattr(self.factory, f'transaction_{prefix}_repo', None)
            if tx_repo and hasattr(tx_repo, 'get_by_portfolio_id'):
                transactions = tx_repo.get_by_portfolio_id(container_id) or []
                total = sum(
                    float(getattr(t, 'quantity', 0))
                    for t in transactions
                    if asset_id is None
                    or getattr(t, 'asset_id', None) == asset_id
                    or getattr(t, 'financial_asset_id', None) == asset_id
                )
                if total:
                    return total

        # 4. Order repo (sum of filled orders for this asset)
        if container_id:
            order_repo = getattr(self.factory, f'order_{prefix}_repo', None)
            if order_repo and hasattr(order_repo, 'get_by_portfolio_id'):
                orders = order_repo.get_by_portfolio_id(container_id) or []
                total = sum(
                    float(getattr(o, 'quantity', 0))
                    for o in orders
                    if asset_id is None
                    or getattr(o, 'asset_id', None) == asset_id
                    or getattr(o, 'financial_asset_id', None) == asset_id
                )
                if total:
                    return total

        return None

    def _get_asset_price_for_holding_value(
        self,
        asset,
        dep_factor_entity,
        date_str: str,
        repository_type: str,
    ) -> Optional[float]:
        """
        Find the price of *asset* at *date_str*.

        Strategy 1 – follow dep_factor_entity's own DB dependencies:
          The holding-value factor has a dependency on a price factor
          (e.g. company_share_price_factor / close).  That price factor's
          FactorValue is stored for *asset* (e.g. CompanyShare), not for
          the holding.  Look it up using the dependency chain.

        Strategy 2 – name-based fallback:
          Try well-known price factor names ('close', 'Close', 'mid_price',
          'price') against the factor_local_repo.
        """
        asset_id   = getattr(asset, 'id', None)
        asset_type = type(asset).__name__
        if not asset_id:
            return None

        # When the holding mapper returns a lightweight placeholder (e.g. _AssetRef),
        # we don't know the real entity type.  Pass None so _check_existing_value
        # skips the entity_type filter and matches on factor_id + entity_id + date only.
        lookup_type = None if asset_type.startswith('_') else asset_type

        factor_dep_repo = getattr(self.factory, 'factor_dependency_local_repo', None)
        factor_local_repo = getattr(self.factory, 'factor_local_repo', None)

        # Strategy 1: use the price-factor deps registered for dep_factor_entity
        if factor_dep_repo and dep_factor_entity.id:
            try:
                deps = factor_dep_repo.get_by_dependent_factor_id(dep_factor_entity.id) or []
                for dep in deps:
                    fv = self._check_existing_value(
                        dep.independent_factor_id, asset_id, lookup_type,
                        date_str, repository_type
                    )
                    if fv:
                        return self._convert_to_float(fv.value)
            except Exception as e:
                self.logger.debug(f"Strategy-1 price lookup failed: {e}")

        # Strategy 2: well-known price factor names
        if factor_local_repo:
            for price_name in ('close', 'Close', 'mid_price', 'price', 'last'):
                try:
                    price_factor = None
                    if hasattr(factor_local_repo, 'get_by_name'):
                        price_factor = factor_local_repo.get_by_name(price_name)
                    if price_factor and price_factor.id:
                        fv = self._check_existing_value(
                            price_factor.id, asset_id, lookup_type,
                            date_str, repository_type
                        )
                        if fv:
                            return self._convert_to_float(fv.value)
                except Exception as e:
                    self.logger.debug(f"Strategy-2 price lookup for '{price_name}' failed: {e}")

        # Strategy 3: currency assets are priced at 1.0 in their own denomination.
        # Cash holdings (e.g. CAD balance in a CAD portfolio) have no price factor
        # record in the DB — their value is simply quantity × 1.
        currency_repo = getattr(self.factory, 'currency_local_repo', None)
        if currency_repo:
            try:
                get_fn = getattr(currency_repo, 'get_by_id', None) or getattr(currency_repo, 'get_by_asset_id', None)
                if get_fn:
                    currency = get_fn(asset_id)
                    if currency is not None:
                        self.logger.debug(
                            f"Asset {asset_id} is a currency — using price 1.0"
                        )
                        return 1.0
            except Exception as e:
                self.logger.debug(f"Strategy-3 currency check failed: {e}")

        return None

    def _try_get_sub_portfolio(self, asset_id) -> Optional[Any]:
        """
        Return a portfolio domain entity for asset_id if it maps to any known
        portfolio type (CompanySharePortfolio, DerivativePortfolio, etc.); None otherwise.

        Checked in specificity order so the most-derived type wins first.
        """
        if not asset_id:
            return None
        repo_keys = (
            'company_share_portfolio_local_repo',
            'company_share_option_portfolio_local_repo',
            'company_share_portfolio_option_portfolio_local_repo',
            'derivative_portfolio_local_repo',
            'portfolio_local_repo',
        )
        for key in repo_keys:
            repo = getattr(self.factory, key, None)
            if repo and hasattr(repo, 'get_by_id'):
                try:
                    result = repo.get_by_id(asset_id)
                    if result is not None:
                        return result
                except Exception:
                    pass
        return None

    def _aggregate_sub_portfolio_holding_value(
        self,
        dep_factor_entity,
        sub_portfolio,
        date_str: str,
        repository_type: str,
    ) -> Optional[FactorValue]:
        """
        Compute the total market value of a sub-portfolio by recursively summing
        the holding values of all its direct holdings.

        Called when a holding's asset is itself a portfolio (e.g.
        CompanySharePortfolioPortfolioHolding), so the normal price × quantity
        formula does not apply at the parent level.
        """
        sub_holdings = self._get_related_entities(sub_portfolio, repository_type)
        if not sub_holdings:
            self.logger.warning(
                f"Sub-portfolio {getattr(sub_portfolio, 'id', '?')} "
                f"({type(sub_portfolio).__name__}) has no holdings; using value 0"
            )
            parsed_date = self._parse_date(date_str)
            return FactorValue(
                id=None,
                factor_id=dep_factor_entity.id,
                entity=sub_portfolio,
                date=parsed_date,
                value='0',
            )

        total = Decimal('0')
        for sub_holding in sub_holdings:
            sub_val = self._resolve_holding_value_factor(
                dep_factor_entity, sub_holding, date_str, repository_type
            )
            if sub_val is not None:
                total += Decimal(str(sub_val.value))
            else:
                self.logger.warning(
                    f"Sub-holding {getattr(sub_holding, 'id', '?')} value could not be "
                    "resolved; treating as 0 for this sub-portfolio aggregation"
                )

        parsed_date = self._parse_date(date_str)
        return self._create_factor_value(
            dep_factor_entity, sub_portfolio, parsed_date, str(total), repository_type
        )

    def _get_related_entities(self, parent_entity, repository_type: str) -> List[Any]:
        """
        Get entities that are related to the parent entity.

        Delegates to the entity's own repository via get_related_entities, so each
        repo decides what "related entities" means for its type.
        """
        try:
            repo = self.factory.get_local_repository(parent_entity.__class__)
            if repo is not None and hasattr(repo, 'get_related_entities'):
                return repo.get_related_entities(parent_entity.id) or []
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
                signature = inspect.signature(calculate_method)
                method_params = list(signature.parameters.keys())

                # Two calling conventions:
                # 1. calculate(dependencies) — receives the whole dict as one arg.
                # 2. calculate(param_a, param_b, …) — individual named params matched
                #    from dependency_values by name.
                call_kwargs = {}
                if 'dependencies' in method_params:
                    call_kwargs['dependencies'] = dependency_values
                else:
                    for param_name in method_params:
                        if param_name in dependency_values:
                            call_kwargs[param_name] = dependency_values[param_name]

                # Add any extra kwargs that match remaining method parameters
                for key, value in kwargs.items():
                    if key in method_params and key not in call_kwargs:
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
        entity,
        target_date: datetime,
        value: str,
        repository_type: str,
    ) -> Optional[FactorValue]:
        """Create and persist factor value to repository.

        Args:
            factor_entity: Factor domain entity instance
            entity: The domain Entity (any Entity subclass). When only an
                    integer id is available, pass None and provide entity_id /
                    entity_type via kwargs instead.
            target_date: Datetime for the factor value
            value: Computed value as string
            repository_type: "local" or "ibkr"
        """
        try:
            # Build FactorValue using the entity object; entity_id and
            # entity_type are derived automatically in __post_init__.
            factor_value = FactorValue(
                id=None,     # Let database auto-increment handle ID
                factor_id=factor_entity.id,
                entity=entity,
                date=target_date,
                value=value,
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
            
            # Extract metadata (support both 'entity' and legacy 'financial_asset_entity' keys)
            financial_asset_entity = factor_batch.metadata.get('entity') or factor_batch.metadata.get('financial_asset_entity')
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
                            entity=financial_asset_entity,
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
            
            # Group entities by entity class for optimized processing
            # Support both 'entity' (new) and 'financial_asset_entity' (legacy) keys
            entities_by_asset_class = {}
            for entity_data in entities_data:
                financial_asset_entity = entity_data.get('entity') or entity_data.get('financial_asset_entity')
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
                            # Support both 'entity' (new) and 'financial_asset_entity' (legacy)
                            sample_entity = entity_data.get('entity') or entity_data.get('financial_asset_entity')

                        if 'time_date' in entity_data:
                            time_date = entity_data['time_date']

                    if factors and entity_ids and sample_entity:
                        # Create FactorBatch for this asset class
                        batch_metadata = {
                            'entity': sample_entity,
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