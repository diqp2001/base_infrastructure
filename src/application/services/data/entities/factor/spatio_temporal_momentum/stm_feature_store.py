"""
STMFeatureStore — persists STM features and signals as FactorValues.

* Feature factors: one CompanyShareSpatioTemporalFeatureFactor row per
  feature name (``<prefix><feature>``), created through its repository.
* Signal factor: CompanyShareSpatioTemporalMomentumFactor.
* Values go to the existing ``factor_values`` table (entity_type
  'CompanyShare'), so downstream code reads ``date -> constituent -> score``
  without knowing anything about the model.

Values are dated with the session date D and are computed from closes up to
and including D.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import (
    bar_key, frequency, next_key,
)

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)

FEATURE_FACTOR_TYPE = "company_share_spatio_temporal_feature_factor"
SIGNAL_FACTOR_TYPE = "company_share_spatio_temporal_momentum_factor"
ENTITY_TYPE = "CompanyShare"


def _as_session_datetime(d, bar_minutes=None) -> datetime:
    return bar_key(d, bar_minutes).to_pydatetime()


class STMFeatureStore:

    def __init__(self, factory, config: STMConfiguration):
        self.factory = factory
        self.config = config

    # ------------------------------------------------------------------
    # Factor rows
    # ------------------------------------------------------------------

    def ensure_feature_factors(self) -> Dict[str, int]:
        """{feature_name: factor_id} in canonical feature order."""
        repo = self.factory.get_local_repository("CompanyShareSpatioTemporalFeatureFactor")
        ids: Dict[str, int] = {}
        for name in self.config.features.feature_names():
            factor = repo._create_or_get(
                repo.get_factor_entity(),
                primary_key=f"{self.config.feature_factor_prefix}{name}",
                group="momentum",
                subgroup="daily" if not self.config.bar_minutes else "minutes",
                frequency=frequency(self.config.bar_minutes),
                factor_type=FEATURE_FACTOR_TYPE,
                definition=f"Spatio-Temporal Momentum input feature: {name}",
            )
            if factor is None or factor.id is None:
                raise RuntimeError(f"Could not create feature factor '{name}'")
            ids[name] = int(factor.id)
        return ids

    def ensure_signal_factor(self):
        repo = self.factory.get_local_repository("CompanyShareSpatioTemporalMomentumFactor")
        factor = repo._create_or_get(
            repo.get_factor_entity(),
            primary_key=self.config.signal_factor_name,
            group="momentum",
            subgroup="daily" if not self.config.bar_minutes else "minutes",
            frequency=frequency(self.config.bar_minutes),
            factor_type=SIGNAL_FACTOR_TYPE,
            definition="Spatio-Temporal Momentum model signal",
        )
        if factor is None or factor.id is None:
            raise RuntimeError("Could not create the Spatio-Temporal Momentum signal factor")
        return factor

    # ------------------------------------------------------------------
    # Bulk writes
    # ------------------------------------------------------------------

    def _existing_keys(self, factor_ids: Iterable[int], entity_ids: Iterable[int], start, end) -> set:
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        session = self.factory.session
        rows = session.query(FactorValueModel.factor_id, FactorValueModel.entity_id, FactorValueModel.date).filter(
            FactorValueModel.factor_id.in_(list(factor_ids)),
            FactorValueModel.entity_id.in_(list(entity_ids)),
            FactorValueModel.date >= _as_session_datetime(start, self.config.bar_minutes),
            FactorValueModel.date <= _as_session_datetime(end, self.config.bar_minutes),
        ).all()
        keys = set()
        for fid, eid, dt in rows:
            ts = pd.Timestamp(dt)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            keys.add((int(fid), int(eid), bar_key(ts, self.config.bar_minutes)))
        return keys

    def _bulk_insert(self, mappings: List[dict]) -> int:
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        if not mappings:
            return 0
        session = self.factory.session
        try:
            session.bulk_insert_mappings(FactorValueModel, mappings)
            session.commit()
        except Exception:
            session.rollback()
            raise
        return len(mappings)

    def write_feature_panel(self, panel, asset_entity_ids: Dict[str, int], start=None, end=None) -> int:
        """Persist every valid (date, asset, feature) value of ``panel`` within [start, end]."""
        factor_ids = self.ensure_feature_factors()
        mask = np.ones(len(panel.dates), dtype=bool)
        mask[: panel.first_valid_row] = False
        if start is not None:
            mask &= panel.dates >= pd.Timestamp(start)
        if end is not None:
            mask &= panel.dates <= pd.Timestamp(end)
        rows = np.where(mask)[0]
        if len(rows) == 0:
            return 0
        existing = self._existing_keys(factor_ids.values(), asset_entity_ids.values(),
                                       panel.dates[rows[0]], panel.dates[rows[-1]])
        mappings = []
        for i in rows:
            d = bar_key(panel.dates[i], self.config.bar_minutes)
            for a_idx, asset in enumerate(panel.assets):
                eid = asset_entity_ids.get(asset)
                if eid is None:
                    continue
                for f_idx, name in enumerate(panel.feature_names):
                    v = panel.features[i, a_idx, f_idx]
                    fid = factor_ids[name]
                    if not np.isfinite(v) or (fid, eid, d) in existing:
                        continue
                    mappings.append({
                        "factor_id": fid, "entity_id": eid, "entity_type": ENTITY_TYPE,
                        "date": d.to_pydatetime(), "value": repr(float(v)),
                    })
        return self._bulk_insert(mappings)

    def write_signals(self, as_of, scores: Dict[int, float]) -> int:
        """Persist one signal per constituent entity id for session ``as_of``."""
        factor = self.ensure_signal_factor()
        d = bar_key(as_of, self.config.bar_minutes)
        existing = self._existing_keys([factor.id], scores.keys(), d, d)
        mappings = [
            {"factor_id": int(factor.id), "entity_id": int(eid), "entity_type": ENTITY_TYPE,
             "date": d.to_pydatetime(), "value": repr(float(s))}
            for eid, s in scores.items()
            if np.isfinite(s) and (int(factor.id), int(eid), d) not in existing
        ]
        return self._bulk_insert(mappings)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def read_signals(self, as_of) -> Dict[int, float]:
        """date -> {constituent entity_id: score} for session ``as_of``."""
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        from src.infrastructure.models.factor.factor import FactorModel
        session = self.factory.session
        fids = [r[0] for r in session.query(FactorModel.id).filter(
            FactorModel.factor_type == SIGNAL_FACTOR_TYPE,
            FactorModel.name == self.config.signal_factor_name,
        ).all()]
        if not fids:
            return {}
        d = bar_key(as_of, self.config.bar_minutes)
        rows = session.query(FactorValueModel.entity_id, FactorValueModel.value).filter(
            FactorValueModel.factor_id.in_(fids),
            FactorValueModel.date >= d.to_pydatetime(),
            FactorValueModel.date < next_key(d, self.config.bar_minutes).to_pydatetime(),
        ).all()
        return {int(eid): float(v) for eid, v in rows}
