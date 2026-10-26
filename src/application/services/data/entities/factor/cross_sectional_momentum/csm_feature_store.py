"""
CSMFeatureStore — the candidate feature values of every cross-sectional decision, as factor values (option C).

The trading cycle computes the 48 candidates in memory with each domain factor's ``calculate()``. With
``CSMConfiguration.persist_features`` it also stores them, so a decision can be audited from the database:
signal (CSMSignalStore) + features (this store) + model artifact + universe membership.

Factor rows: the SAME factors the factor-resolution path uses. For every DependencySpec of
CompanyShareCrossSectionalMomentumFactor (one per candidate), an existing factor that ``spec.matches_factor`` (the
resolver's own matching rule, parent = the configured signal factor) is reused; otherwise one is created with the
resolver's creation rules (class defaults, the spec's group / frequency, SELF resolved against the signal factor,
source = the spec's source or first ``source_in``). Resolving the signal through FactorValueResolutionService
therefore finds these factors instead of creating others.

Values: one per (candidate, asset) of the decision, dated like the signal (the bar the decision used: the session,
or the 10-minute bar), never overwritten (a value already stored for that bar is kept).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
    CSMFeatureDefinition,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_signal_store import (
    ENTITY_TYPE,
    CSMSignalStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key

logger = logging.getLogger(__name__)


def candidate_specs() -> Dict[str, object]:
    """{feature name: DependencySpec} of CompanyShareCrossSectionalMomentumFactor."""
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import (
        cross_sectional_feature_dependency_specs,
    )
    by_class = {cls_name: name for cls_name, name in CSMFeatureDefinition.FEATURE_MAP}
    return {by_class[spec.factor_type.__name__]: spec for spec in cross_sectional_feature_dependency_specs()
            if spec.factor_type.__name__ in by_class}


def _creation_kwargs(spec, parent) -> Dict[str, object]:
    """The resolver's rules (FactorValueResolutionService._resolve_dependency_spec) for a calculated dependency."""
    from src.domain.entities.factor.dependency_spec import DependencySpec

    def resolve(value, attr):
        return getattr(parent, attr, None) if value is DependencySpec.SELF else value

    obj = spec.factor_type()
    defaults = {k: getattr(obj, k, None) for k in ("group", "subgroup", "frequency", "data_type")}
    source = resolve(spec.source, "source") or (spec.source_in[0] if spec.source_in else None) \
        or getattr(parent, "source", None)
    kwargs = {
        "group": resolve(spec.group, "group") or defaults["group"],
        "subgroup": resolve(spec.subgroup, "subgroup") or defaults["subgroup"],
        "frequency": resolve(spec.frequency, "frequency") or defaults["frequency"],
        "data_type": resolve(spec.data_type, "data_type") or defaults["data_type"],
        "source": source,
    }
    return {k: v for k, v in kwargs.items() if v is not None}


class CSMFeatureStore:

    def __init__(self, factory, config: CSMConfiguration, signal_store: Optional[CSMSignalStore] = None):
        self.factory = factory
        self.config = config
        self.signal_store = signal_store or CSMSignalStore(factory, config)
        self._factor_ids: Optional[Dict[str, int]] = None

    def ensure_feature_factors(self) -> Dict[str, int]:
        """{candidate feature name: factor id} of the configured candidates (excluded ones are not created)."""
        if self._factor_ids is not None:
            return self._factor_ids
        parent = self.signal_store.ensure_signal_factor()
        wanted = set(self.config.features.base_feature_names())
        ids: Dict[str, int] = {}
        for name, spec in candidate_specs().items():
            if name not in wanted:
                continue
            repo = self.factory.get_local_repository(spec.dep_name)
            if repo is None:
                raise RuntimeError(f"no repository for '{spec.dep_name}' (feature '{name}')")
            matching = [f for f in (repo.get_all() or []) if spec.matches_factor(parent, f)]
            if matching:
                factor = min(matching, key=lambda f: f.id)
                if len(matching) > 1:
                    logger.warning(f"{len(matching)} factors match the '{name}' dependency; values go to id "
                                   f"{factor.id} (the resolver reads all of them)")
            else:
                factor = repo._create_or_get(spec.factor_type, spec.factor_type().name,
                                             **_creation_kwargs(spec, parent))
                if factor is None or getattr(factor, "id", None) is None:
                    raise RuntimeError(f"could not create the factor of feature '{name}'")
                if not spec.matches_factor(parent, factor):
                    raise RuntimeError(f"the factor created for feature '{name}' does not match its dependency spec "
                                       f"(the resolver would not find it)")
            ids[name] = int(factor.id)
        self._factor_ids = ids
        return ids

    def write(self, session, rows: pd.DataFrame, ticker_to_entity: Dict[str, int]) -> int:
        """``rows``: index = ticker, columns = candidate feature names (the decision's feature rows)."""
        from src.domain.entities.factor.factor_value import FactorValue
        ids = self.ensure_feature_factors()
        d = bar_key(session, self.config.bar_minutes).to_pydatetime()
        values = []
        for ticker, row in rows.iterrows():
            eid = ticker_to_entity.get(ticker)
            if eid is None:
                continue
            for name, fid in ids.items():
                v = row.get(name, np.nan)
                if v is None or not np.isfinite(v):
                    continue
                values.append(FactorValue(id=None, factor_id=fid, entity=None, date=d, value=repr(float(v)),
                                          entity_type=ENTITY_TYPE, entity_id=int(eid)))
        return self.factory.factor_value_local_repo.add_bulk(values)
