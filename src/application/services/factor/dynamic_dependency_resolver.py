"""
src/application/services/factor/dynamic_dependency_resolver.py

Application service for resolving factor dependencies dynamically at calculation time.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, date
from collections import defaultdict
import logging

from src.domain.entities.factor.dynamic_dependency_requirements import DependencyRequirements
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.factor import Factor


class DynamicDependencyResolver:
    """
    Application service for dynamic dependency resolution at factor calculation time.
    
    This service provides date-aware dependency discovery that adapts to data availability
    rather than relying on fixed dependency relationships.
    """

    def __init__(self, factory):
        """
        Initialize dynamic dependency resolver.
        
        Args:
            factory: Repository factory for accessing data
        """
        self.factory = factory
        self.logger = logging.getLogger(__name__)

    def discover_dependencies(
        self,
        requirements: DependencyRequirements,
        entity: Any,
        target_date: datetime,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Discover available dependencies for a factor at a specific date.
        
        Args:
            requirements: Dependency requirements specification
            entity: Financial asset entity the factor is calculated for
            target_date: Date for which to find dependencies
            **kwargs: Additional parameters for discovery
            
        Returns:
            List of discovered dependency information dictionaries
        """
        try:
            self.logger.info(f"Discovering dependencies for entity {entity.id} at {target_date}")
            
            # 1. Find candidate factors that match requirements
            candidate_factors = self._find_candidate_factors(requirements, entity)
            if not candidate_factors:
                self.logger.warning("No candidate factors found matching requirements")
                return []
            
            # 2. Filter by data availability at target date
            available_factors = self._filter_by_availability(
                candidate_factors, entity, target_date, requirements.max_age_days
            )
            
            # 3. Apply source preferences and limits
            prioritized_factors = self._prioritize_by_source(available_factors, requirements)
            
            # 4. Handle entity relationships (e.g., underlying asset dependencies)
            relationship_factors = self._resolve_entity_relationships(
                prioritized_factors, entity, target_date, requirements
            )
            
            # 5. Apply fallback strategies if needed
            final_factors = self._apply_fallback_strategies(
                relationship_factors, requirements, entity, target_date
            )
            
            self.logger.info(f"Discovered {len(final_factors)} dependencies")
            return final_factors
            
        except Exception as e:
            self.logger.error(f"Error discovering dependencies: {e}")
            return []

    def resolve_values(
        self,
        dependencies: List[Dict[str, Any]],
        target_date: datetime,
        entity_id: int
    ) -> Dict[str, Any]:
        """
        Resolve actual values for discovered dependencies.
        
        Args:
            dependencies: List of dependency information from discover_dependencies
            target_date: Target calculation date
            entity_id: Entity ID for factor values
            
        Returns:
            Dictionary mapping parameter names to resolved values
        """
        try:
            resolved_values = {}
            
            for dep_info in dependencies:
                param_name = dep_info.get('parameter_name')
                factor = dep_info.get('factor')
                lag = dep_info.get('lag', timedelta(0))
                dep_entity_id = dep_info.get('entity_id', entity_id)
                
                if not param_name or not factor:
                    continue
                
                # Calculate adjusted date considering lag
                dependency_date = target_date - lag
                date_str = dependency_date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Try to get existing value from database
                factor_value = self._get_factor_value_from_db(
                    factor.id, dep_entity_id, date_str
                )
                
                if factor_value:
                    resolved_values[param_name] = float(factor_value.value)
                    self.logger.debug(f"Resolved {param_name} = {factor_value.value} from DB")
                else:
                    # Try to create missing dependency value
                    created_value = self._create_missing_dependency(
                        factor, dep_entity_id, dependency_date
                    )
                    if created_value:
                        resolved_values[param_name] = float(created_value.value)
                        self.logger.debug(f"Created {param_name} = {created_value.value}")
            
            return resolved_values
            
        except Exception as e:
            self.logger.error(f"Error resolving dependency values: {e}")
            return {}

    def _find_candidate_factors(
        self,
        requirements: DependencyRequirements,
        entity: Any
    ) -> List[Factor]:
        """Find factors that match dependency requirements."""
        try:
            if not self.factory or not self.factory.factor_local_repo:
                return []
            
            # Get all factors from database
            all_factors = self.factory.factor_local_repo.get_all()
            
            # Filter by requirements
            candidates = []
            for factor in all_factors:
                if requirements.matches_factor(factor):
                    candidates.append(factor)
            
            self.logger.debug(f"Found {len(candidates)} candidate factors")
            return candidates
            
        except Exception as e:
            self.logger.error(f"Error finding candidate factors: {e}")
            return []

    def _filter_by_availability(
        self,
        factors: List[Factor],
        entity: Any,
        target_date: datetime,
        max_age_days: int
    ) -> List[Dict[str, Any]]:
        """Filter factors by data availability at target date."""
        try:
            available = []
            entity_id = getattr(entity, 'id')
            
            # Calculate acceptable date range
            max_age = timedelta(days=max_age_days)
            earliest_date = target_date - max_age
            
            for factor in factors:
                # Check if factor has values for this entity around target date
                latest_value = self._get_latest_factor_value_before_date(
                    factor.id, entity_id, target_date
                )
                
                if latest_value and latest_value.date >= earliest_date.date():
                    available.append({
                        'factor': factor,
                        'latest_value': latest_value,
                        'age_days': (target_date.date() - latest_value.date).days,
                        'entity_id': entity_id
                    })
            
            self.logger.debug(f"Found {len(available)} factors with available data")
            return available
            
        except Exception as e:
            self.logger.error(f"Error filtering by availability: {e}")
            return []

    def _prioritize_by_source(
        self,
        available_factors: List[Dict[str, Any]],
        requirements: DependencyRequirements
    ) -> List[Dict[str, Any]]:
        """Prioritize factors by source preferences."""
        try:
            # Group by factor name/group to handle multiple sources
            grouped = defaultdict(list)
            for factor_info in available_factors:
                factor = factor_info['factor']
                key = (factor.name, factor.group, factor.subgroup)
                grouped[key].append(factor_info)
            
            prioritized = []
            for factor_group in grouped.values():
                # Sort by source priority
                factor_group.sort(
                    key=lambda x: requirements.get_source_priority_score(x['factor'].source),
                    reverse=True
                )
                
                # Apply source limits
                if requirements.max_sources:
                    factor_group = factor_group[:requirements.max_sources]
                
                prioritized.extend(factor_group)
            
            return prioritized
            
        except Exception as e:
            self.logger.error(f"Error prioritizing by source: {e}")
            return available_factors

    def _resolve_entity_relationships(
        self,
        factors: List[Dict[str, Any]],
        entity: Any,
        target_date: datetime,
        requirements: DependencyRequirements
    ) -> List[Dict[str, Any]]:
        """Resolve entity relationship dependencies (e.g., underlying asset)."""
        try:
            resolved_factors = []
            
            for factor_info in factors:
                # Default to same entity
                factor_info['entity_id'] = getattr(entity, 'id')
                factor_info['parameter_name'] = factor_info['factor'].name
                factor_info['lag'] = timedelta(0)
                
                # Check if this dependency should use related entity
                if requirements.entity_relationship_keys:
                    for rel_key in requirements.entity_relationship_keys:
                        if hasattr(entity, rel_key):
                            related_entity_id = getattr(entity, rel_key)
                            if related_entity_id and related_entity_id != entity.id:
                                factor_info['entity_id'] = related_entity_id
                                factor_info['parameter_name'] = f"{rel_key}_{factor_info['factor'].name}"
                                break
                
                resolved_factors.append(factor_info)
            
            return resolved_factors
            
        except Exception as e:
            self.logger.error(f"Error resolving entity relationships: {e}")
            return factors

    def _apply_fallback_strategies(
        self,
        factors: List[Dict[str, Any]],
        requirements: DependencyRequirements,
        entity: Any,
        target_date: datetime
    ) -> List[Dict[str, Any]]:
        """Apply fallback strategies if insufficient dependencies found."""
        try:
            if not requirements.fallback_strategies:
                return factors
            
            # Count available sources
            sources = set(f['factor'].source for f in factors)
            
            if not requirements.should_apply_fallback(len(factors), sources):
                return factors
            
            # Apply each fallback strategy
            for strategy in requirements.fallback_strategies:
                if strategy == "use_close_if_no_mid":
                    factors = self._fallback_use_close_for_mid(factors, requirements, entity, target_date)
                elif strategy == "single_source_ok":
                    factors = self._fallback_allow_single_source(factors, requirements)
                elif strategy == "use_older_data":
                    factors = self._fallback_use_older_data(factors, requirements, entity, target_date)
            
            return factors
            
        except Exception as e:
            self.logger.error(f"Error applying fallback strategies: {e}")
            return factors

    def _fallback_use_close_for_mid(
        self,
        factors: List[Dict[str, Any]],
        requirements: DependencyRequirements,
        entity: Any,
        target_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fallback: use close price if mid price not available."""
        try:
            has_mid_price = any(
                f['factor'].subgroup == 'mid_price' for f in factors
            )
            
            if not has_mid_price and 'mid_price' in (requirements.required_subgroups or []):
                # Look for close price as fallback
                close_factors = self._find_candidate_factors(
                    DependencyRequirements(
                        required_groups=requirements.required_groups,
                        required_subgroups=['close'],
                        min_sources=1,
                        max_age_days=requirements.max_age_days
                    ),
                    entity
                )
                
                available_close = self._filter_by_availability(
                    close_factors, entity, target_date, requirements.max_age_days
                )
                
                if available_close:
                    self.logger.info("Applied fallback: using close price for mid price")
                    factors.extend(available_close)
            
            return factors
            
        except Exception as e:
            self.logger.error(f"Error in close price fallback: {e}")
            return factors

    def _fallback_allow_single_source(
        self,
        factors: List[Dict[str, Any]],
        requirements: DependencyRequirements
    ) -> List[Dict[str, Any]]:
        """Fallback: allow single source if multiple not available."""
        if not requirements.allow_single_source and len(factors) == 1 and requirements.min_sources > 1:
            self.logger.info("Applied fallback: allowing single source")
            # Temporarily override min_sources requirement
            requirements.min_sources = 1
        
        return factors

    def _fallback_use_older_data(
        self,
        factors: List[Dict[str, Any]],
        requirements: DependencyRequirements,
        entity: Any,
        target_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fallback: use older data if recent data not available."""
        try:
            if len(factors) < requirements.min_sources and requirements.allow_older_data:
                # Extend search to older data
                extended_age = requirements.max_age_days * 3  # Look back 3x longer
                
                candidate_factors = self._find_candidate_factors(requirements, entity)
                older_factors = self._filter_by_availability(
                    candidate_factors, entity, target_date, extended_age
                )
                
                # Add factors not already present
                existing_factor_ids = set(f['factor'].id for f in factors)
                for factor_info in older_factors:
                    if factor_info['factor'].id not in existing_factor_ids:
                        self.logger.info(f"Applied fallback: using older data for factor {factor_info['factor'].name}")
                        factors.append(factor_info)
            
            return factors
            
        except Exception as e:
            self.logger.error(f"Error in older data fallback: {e}")
            return factors

    def _get_factor_value_from_db(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str
    ) -> Optional[FactorValue]:
        """Get factor value from database."""
        try:
            if not self.factory or not self.factory.factor_value_local_repo:
                return None
            
            return self.factory.factor_value_local_repo.get_by_factor_entity_date(
                factor_id, entity_id, date_str
            )
            
        except Exception as e:
            self.logger.error(f"Error getting factor value from DB: {e}")
            return None

    def _get_latest_factor_value_before_date(
        self,
        factor_id: int,
        entity_id: int,
        target_date: datetime
    ) -> Optional[FactorValue]:
        """Get latest factor value before or on target date."""
        try:
            if not self.factory or not self.factory.factor_value_local_repo:
                return None
            
            return self.factory.factor_value_local_repo.get_latest_by_factor_entity(
                factor_id, entity_id
            )
            
        except Exception as e:
            self.logger.error(f"Error getting latest factor value: {e}")
            return None

    def _create_missing_dependency(
        self,
        factor: Factor,
        entity_id: int,
        dependency_date: datetime
    ) -> Optional[FactorValue]:
        """Create missing dependency value using IBKR or other sources."""
        try:
            # Get the entity to create the dependency for
            entity = self.factory.financial_asset_local_repo.get_by_id(entity_id)
            if not entity:
                return None
            
            # Use IBKR factor value repository to create missing value
            if self.factory.factor_value_ibkr_repo:
                return self.factory.factor_value_ibkr_repo._create_or_get(
                    entity_symbol=None,
                    factor=factor,
                    entity=entity,
                    date=dependency_date.strftime("%Y-%m-%d %H:%M:%S")
                )
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating missing dependency: {e}")
            return None