# Factor Value Local Repository
# Mirrors src/infrastructure/models/factor/factor_value.py

import inspect
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError
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
            if entity.currency_id is None:
                entity.currency_id = self._resolve_currency_id(entity)
            model = self._to_model(entity)
            self.session.add(model)
            self.session.commit()
            return self._to_entity(model)
        except IntegrityError as e:
            # The natural key (factor, entity, entity type, date) is already stored — typically another
            # writer that resolved the same value concurrently. Never a second row: return the stored one.
            self.session.rollback()
            stored = self._stored_with_same_key(model)
            if stored is None:
                print(f"Error adding factor value: {e}")
                return None
            if str(stored.value) != str(model.value):
                print(f"Factor value already stored for factor {model.factor_id}, {model.entity_type}:"
                      f"{model.entity_id} at {model.date}: kept {stored.value}, ignored {model.value} "
                      f"(use update to replace it)")
            return stored
        except Exception as e:
            print(f"Error adding factor value: {e}")
            self.session.rollback()
            return None

    def add_bulk(self, entities: List[FactorValue]) -> int:
        """Insert many values in one transaction; values whose natural key (factor, entity, entity type, date) is
        already stored are skipped (never overwritten). Returns the number inserted. Rows are built through the ORM
        constructor so value_numeric is filled like add() does."""
        entities = [e for e in entities if e is not None]
        if not entities:
            return 0
        keyed = {}
        for e in entities:
            keyed.setdefault((int(e.factor_id), int(e.entity_id), e.entity_type, e.date), e)
        factor_ids = {k[0] for k in keyed}
        entity_ids = {k[1] for k in keyed}
        dates = [k[3] for k in keyed]
        existing = set()
        for fid, eid, etype, d in (self.session.query(FactorValueModel.factor_id, FactorValueModel.entity_id,
                                                      FactorValueModel.entity_type, FactorValueModel.date)
                                   .filter(FactorValueModel.factor_id.in_(factor_ids),
                                           FactorValueModel.entity_id.in_(entity_ids),
                                           FactorValueModel.date >= min(dates), FactorValueModel.date <= max(dates))):
            d = d.replace(tzinfo=None) if getattr(d, "tzinfo", None) is not None else d
            existing.add((int(fid), int(eid), etype, d))
        currencies: Dict[int, Optional[int]] = {}
        models = []
        for key, e in keyed.items():
            plain_date = key[3].replace(tzinfo=None) if getattr(key[3], "tzinfo", None) is not None else key[3]
            if (key[0], key[1], key[2], plain_date) in existing:
                continue
            if e.currency_id is None:
                if e.entity_id not in currencies:
                    currencies[e.entity_id] = self._resolve_currency_id(e)
                e.currency_id = currencies[e.entity_id]
            models.append(self._to_model(e))
        if not models:
            return 0
        try:
            self.session.add_all(models)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return len(models)

    def _stored_with_same_key(self, model: FactorValueModel) -> Optional[FactorValue]:
        """The stored value with the natural key of the row that could not be inserted, or None."""
        stored = (self.session.query(FactorValueModel)
                  .filter(FactorValueModel.factor_id == model.factor_id,
                          FactorValueModel.entity_id == model.entity_id,
                          FactorValueModel.entity_type == model.entity_type,
                          FactorValueModel.date == model.date)
                  .first())
        return self._to_entity(stored) if stored is not None else None

    def _invalidate_dependents(self, model: FactorValueModel) -> None:
        """A stored value changed (an upstream correction, or a recomputed derived value): every value computed
        from it is marked STALE and recomputed on its next read instead of being reused (BI-028)."""
        provenance = getattr(self.factory, 'observation_provenance_local_repo', None) if self.factory else None
        if provenance is None:
            return
        from src.domain.entities.factor.observation_quality import ObservationRef
        ref = ObservationRef(model.factor_id, model.entity_type, model.entity_id, model.date)
        affected = provenance.invalidate_dependents(ref, f"input {ref} changed to {model.value}")
        if affected:
            print(f"Factor value {ref} changed: {len(affected)} dependent value(s) marked stale")

    def _resolve_currency_id(self, entity: FactorValue) -> Optional[int]:
        """Look up currency_id from the associated financial entity (any type)."""
        try:
            if entity.entity_id is not None:
                from src.infrastructure.models.finance.financial_entity import FinancialEntityModel
                fe = self.session.get(FinancialEntityModel, entity.entity_id)
                if fe is not None:
                    currency_id = getattr(fe, 'currency_id', None)
                    if currency_id is not None:
                        return currency_id
        except Exception:
            pass
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
            # Resolve entity_id from entity object when available
            model.entity_id = (
                entity.entity.id if entity.entity is not None else entity.entity_id
            )
            model.entity_type = (
                type(entity.entity).__name__
                if entity.entity is not None
                else entity.entity_type
            )
            model.date = entity.date
            changed = str(model.value) != str(entity.value)
            model.value = entity.value

            self.session.commit()
            if changed:
                self._invalidate_dependents(model)
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
    
    def get_bar_times(self, factor_id: int, entity_id: int, entity_type: str, start: datetime,
                      end: datetime) -> List[datetime]:
        """Timestamps of the stored values of one series in [start, end] that hold a value (BI-029 coverage)."""
        rows = (self.session.query(FactorValueModel.date)
                .filter(FactorValueModel.factor_id == factor_id,
                        FactorValueModel.entity_id == entity_id,
                        FactorValueModel.entity_type == entity_type,
                        FactorValueModel.date >= start, FactorValueModel.date <= end,
                        FactorValueModel.value.isnot(None), FactorValueModel.value != "")
                .order_by(FactorValueModel.date).all())
        return [d for (d,) in rows]

    def get_values_panel(self, factor_ids: List[int], entity_ids: List[int], entity_type: str,
                         start: datetime, end: datetime) -> List[tuple]:
        """[(factor_id, entity_id, date, float value)] of the given factors and entities in [start, end], in one
        query (research reads). The numeric copy is used when present, the text value otherwise; values that are
        not numbers are left out."""
        if not factor_ids or not entity_ids:
            return []
        rows = (self.session.query(FactorValueModel.factor_id, FactorValueModel.entity_id, FactorValueModel.date,
                                   FactorValueModel.value_numeric, FactorValueModel.value)
                .filter(FactorValueModel.factor_id.in_([int(f) for f in factor_ids]),
                        FactorValueModel.entity_id.in_([int(e) for e in entity_ids]),
                        FactorValueModel.entity_type == entity_type,
                        FactorValueModel.date >= start, FactorValueModel.date <= end)
                .all())
        out = []
        for fid, eid, d, numeric, text in rows:
            v = numeric
            if v is None:
                try:
                    v = float(text)
                except (TypeError, ValueError):
                    continue
            if getattr(d, "tzinfo", None) is not None:
                d = d.replace(tzinfo=None)
            out.append((int(fid), int(eid), d, float(v)))
        return out

    def get_all_dates_by_id_entity_id(
        self, factor_id: int, entity_id: int, entity_type: Optional[str] = None
    ) -> List[str]:
        """Get all dates for a specific factor and entity combination.

        Args:
            factor_id: Factor id
            entity_id: Raw entity id
            entity_type: Optional entity class name discriminator. When provided
                the query is scoped to that entity type to prevent id collisions
                across different entity tables.
        """
        try:
            query = self.session.query(FactorValueModel.date).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
            )
            if entity_type is not None:
                query = query.filter(FactorValueModel.entity_type == entity_type)

            dates = query.all()
            return [str(date_tuple[0]) for date_tuple in dates]
        except Exception as e:
            print(f"Error getting dates for factor {factor_id} and entity {entity_id}: {e}")
            return []

    def get_by_factor_entity_date(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str,
        entity_type: Optional[str] = None,
    ) -> Optional[FactorValue]:
        """Get factor value by factor ID, entity ID (+ optional entity type), and date.

        The ``entity_type`` discriminator prevents false matches when different
        entity tables share the same numeric ids (e.g. Country id=1 and
        CompanyShare id=1 both producing entity_id=1).
        """
        try:
            # Convert date string to datetime object
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

            query = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date == date_obj,
            )
            if entity_type is not None:
                query = query.filter(FactorValueModel.entity_type == entity_type)

            model = query.first()
            return self._to_entity(model)
        except Exception as e:
            print(
                f"Error getting factor value for factor {factor_id}, "
                f"entity {entity_type}:{entity_id}, date {date_str}: {e}"
            )
            return None

    def get_most_recent_before(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str,
        entity_type: Optional[str] = None,
    ) -> Optional[FactorValue]:
        """Return the most recent stored value for (factor, entity) with date ≤ target.

        Used as a fallback for IBKR-sourced factors whose stored bar timestamp
        (e.g. 09:30:00) lags behind the algorithm's resolution time (e.g. 09:35:00).
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            query = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date <= date_obj,
            )
            if entity_type is not None:
                query = query.filter(FactorValueModel.entity_type == entity_type)
            model = query.order_by(FactorValueModel.date.desc()).first()
            return self._to_entity(model)
        except Exception as e:
            print(
                f"Error in get_most_recent_before for factor {factor_id}, "
                f"entity {entity_type}:{entity_id}, date {date_str}: {e}"
            )
            return None

    def get_latest_available_bar(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str,
        bar_seconds: int,
        max_staleness_seconds: Optional[float] = None,
        entity_type: Optional[str] = None,
        require_current: bool = False,
    ) -> Optional[FactorValue]:
        """Return the latest raw bar value whose bar had CLOSED at ``date_str``.

        Bars are stamped with their start time.  A bar has closed at ``target``
        when either ``start + bar_seconds <= target`` or a later bar has already
        started by ``target`` (this trims session-truncated bars, e.g. an 8h
        bar stamped 09:30 that ends when the 12:00 bar starts).  Only closed bars
        are eligible, which prevents look-ahead.  When ``max_staleness_seconds``
        is given, a bar that closed longer ago than that is ignored (returns
        None so the caller can fetch fresh data). ``require_current`` applies the
        trading-calendar rule instead (bar_calendar.bar_is_current): None as soon as
        a newer bar should have closed — a missing bar is fetched, never replaced by
        an older one.
        """
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            query = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date <= target,
            )
            if entity_type is not None:
                query = query.filter(FactorValueModel.entity_type == entity_type)
            # The two latest bars that started by target: the newest may still
            # be open; the one before it is closed because its successor started.
            rows = query.order_by(FactorValueModel.date.desc()).limit(2).all()
            if not rows:
                return None

            def _naive(dt):
                return dt.replace(tzinfo=None) if getattr(dt, 'tzinfo', None) else dt

            newest = rows[0]
            newest_start = _naive(newest.date)
            if newest_start + timedelta(seconds=bar_seconds) <= target:
                chosen, chosen_close = newest, newest_start + timedelta(seconds=bar_seconds)
            elif len(rows) > 1:
                prev_start = _naive(rows[1].date)
                chosen = rows[1]
                chosen_close = min(prev_start + timedelta(seconds=bar_seconds), newest_start)
            else:
                return None

            if max_staleness_seconds is not None:
                if (target - chosen_close).total_seconds() > max_staleness_seconds:
                    return None
            if require_current:
                from src.domain.entities.factor.bar_calendar import bar_is_current
                if not bar_is_current(_naive(chosen.date), chosen_close, target, bar_seconds):
                    return None
            return self._to_entity(chosen)
        except Exception as e:
            print(
                f"Error in get_latest_available_bar for factor {factor_id}, "
                f"entity {entity_type}:{entity_id}, date {date_str}: {e}"
            )
            return None

    def get_closed_bar_series(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str,
        bar_seconds: int,
        count: Optional[int] = None,
        since: Optional[datetime] = None,
        max_staleness_seconds: Optional[float] = None,
        entity_type: Optional[str] = None,
        require_current: bool = False,
    ) -> List[float]:
        """Trailing values of a raw bar factor at ``date_str``, oldest first, as floats (see
        get_closed_bar_values for the rule)."""
        values = self.get_closed_bar_values(factor_id, entity_id, date_str, bar_seconds, count=count, since=since,
                                            max_staleness_seconds=max_staleness_seconds, entity_type=entity_type,
                                            require_current=require_current)
        return [float(v.value) for v in values if v.value is not None]

    def get_closed_bar_values(
        self,
        factor_id: int,
        entity_id: int,
        date_str: str,
        bar_seconds: int,
        count: Optional[int] = None,
        since: Optional[datetime] = None,
        max_staleness_seconds: Optional[float] = None,
        entity_type: Optional[str] = None,
        require_current: bool = False,
    ) -> List[FactorValue]:
        """Trailing stored values of a raw bar factor at ``date_str``, oldest first.

        The newest value is the one get_latest_available_bar returns (closed bar, staleness rule);
        the series runs back from it: ``count`` values, or every value from ``since`` plus the last
        value before ``since`` (the base of a year-to-date return). [] when no closed bar is available.
        """
        try:
            latest = self.get_latest_available_bar(factor_id, entity_id, date_str, bar_seconds,
                                                   max_staleness_seconds=max_staleness_seconds,
                                                   entity_type=entity_type, require_current=require_current)
            if latest is None:
                return []
            anchor = latest.date.replace(tzinfo=None) if getattr(latest.date, 'tzinfo', None) else latest.date
            query = self.session.query(FactorValueModel).filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date <= anchor,
            )
            if entity_type is not None:
                query = query.filter(FactorValueModel.entity_type == entity_type)
            if since is not None:
                rows = query.filter(FactorValueModel.date >= since).order_by(FactorValueModel.date).all()
                base = query.filter(FactorValueModel.date < since).order_by(FactorValueModel.date.desc()).first()
                rows = ([base] if base is not None else []) + rows
            else:
                rows = list(reversed(query.order_by(FactorValueModel.date.desc()).limit(count).all()))
            return [self._to_entity(r) for r in rows if r.value is not None]
        except Exception as e:
            print(f"Error in get_closed_bar_values for factor {factor_id}, entity {entity_type}:{entity_id}, "
                  f"date {date_str}: {e}")
            return []

    def _create_or_get(self, entity_symbol, primary_key=None, **kwargs) -> Optional[FactorValue]:
        """
        Enhanced get_or_create with automatic dependency resolution via FactorValueResolutionService.

        Args:
            entity_symbol: Symbol identifier (kept for API compatibility, not used directly)
            primary_key: Optional primary key (not used in this implementation)
            **kwargs: Parameters including:
                - factor: Factor domain entity instance
                - entity: Domain Entity (any Entity subclass – Country, CompanyShare, Portfolio, …)
                - date: Date string in 'YYYY-MM-DD HH:MM:SS' format
                - value: Optional explicit value to use

        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            factor_entity = kwargs.get('factor')
            entity = kwargs.get('entity')
            time_date = kwargs.get('date', datetime.now())

            if not factor_entity:
                print("Factor entity is required for local factor value creation")
                return None

            if entity is None:
                print("Entity is required for local factor value creation")
                return None

            # Remove keys already passed as explicit arguments to avoid duplicate keyword errors
            extra_kwargs = {k: v for k, v in kwargs.items() if k not in ('factor', 'entity', 'date')}

            # Use the resolution service to handle the factor value creation
            return self.resolution_service.resolve_factor_value(
                factor_entity=factor_entity,
                entity=entity,
                time_date=time_date,
                repository_type="local",
                **extra_kwargs
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
                # Create new factor value entity with calculated result.
                # entity_id and entity_type are stored directly (no entity object here).
                factor_value = FactorValue(
                    id=None,
                    factor_id=factor.id,
                    entity=None,
                    date=target_date,
                    value=str(calculated_value),
                    entity_id=entity_id,
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

    def _create_or_get_legacy(
        self,
        factor_id: int,
        entity_id: int,
        date: date,
        value: str,
        entity_type: Optional[str] = None,
    ) -> Optional[FactorValue]:
        """Legacy create or get method for backward compatibility.

        Note: prefer passing ``entity_type`` to avoid id collisions across
        different entity tables.
        """
        # Check if entity already exists by factor_id, entity_id, and date
        existing = self.get_by_factor_entity_date(
            factor_id, entity_id, str(date), entity_type=entity_type
        )
        if existing:
            return existing

        try:
            factor_value = FactorValue(
                id=None,   # Let database auto-increment handle ID generation
                factor_id=factor_id,
                entity=None,
                date=date,
                value=value,
                entity_id=entity_id,
                entity_type=entity_type,
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

    def resolve_batch(self, factor_entity, entities, target_dates, repository_type="local", **kwargs):
        """
        Resolve factor values for multiple entities across multiple dates using
        FactorValueBatchResolutionService (DFS topological order, lag propagation).

        Args:
            factor_entity: Root Factor domain entity to resolve.
            entities: List of domain entities (e.g. CompanyShare) to resolve for.
            target_dates: List of datetime objects — dates to resolve the root factor at.
            repository_type: "local" (default) or "ibkr".
            **kwargs: Forwarded to the underlying resolver.

        Returns:
            BatchResolutionResult with execution_order, resolved_values, and failed entries.
        """
        from src.application.services.data.entities.factor.factor_value_batch_resolution_service import (
            FactorValueBatchResolutionService,
        )
        svc = FactorValueBatchResolutionService(factory=self.factory)
        return svc.resolve_batch(factor_entity, entities, target_dates, repository_type, **kwargs)