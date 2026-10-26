"""
Signals of the cross-sectional momentum classifier as factor values, through the repositories only:

    CSMSignalStore            the trading cycle writes one probability per constituent and decision session
                              (factor CompanyShareCrossSectionalMomentumFactor, name = config.signal_factor_name)
    CSMStoredSignalProvider   reads a stored decision back (used by CSMModelProvider, the factor's provider)
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import frequency

ENTITY_TYPE = "CompanyShare"
SIGNAL_FACTOR_TYPE = "company_share_cross_sectional_momentum_factor"


def _date_key(session) -> pd.Timestamp:
    return pd.Timestamp(session).normalize()


class CSMSignalStore:

    def __init__(self, factory, config: CSMConfiguration):
        self.factory = factory
        self.config = config
        self._factor = None

    def ensure_signal_factor(self):
        if self._factor is None:
            repo = self.factory.get_local_repository("CompanyShareCrossSectionalMomentumFactor")
            factor = repo._create_or_get(
                repo.get_factor_entity(), primary_key=self.config.signal_factor_name, group="momentum",
                subgroup="minutes" if self.config.bar_minutes else "daily",
                frequency=frequency(self.config.bar_minutes), factor_type=SIGNAL_FACTOR_TYPE,
                definition="Cross-sectional momentum classifier: probability of beating the cross-sectional median",
            )
            if factor is None or factor.id is None:
                raise RuntimeError("Could not create the cross-sectional momentum signal factor")
            self._factor = factor
        return self._factor

    def write(self, session, probabilities: Dict[int, float]) -> int:
        """One value per constituent entity id; values already stored for the session are kept."""
        from src.domain.entities.factor.factor_value import FactorValue
        factor = self.ensure_signal_factor()
        repo = self.factory.factor_value_local_repo
        d = _date_key(session).to_pydatetime()
        written = 0
        for eid, p in probabilities.items():
            if p is None or not np.isfinite(p):
                continue
            if repo.get_by_factor_entity_date(int(factor.id), int(eid), d.strftime("%Y-%m-%d %H:%M:%S"),
                                              ENTITY_TYPE) is not None:
                continue
            if repo.add(FactorValue(id=None, factor_id=int(factor.id), entity=None, date=d, value=repr(float(p)),
                                    entity_type=ENTITY_TYPE, entity_id=int(eid))) is not None:
                written += 1
        return written

    def read(self, session, entity_id: int) -> Optional[float]:
        factor = self.ensure_signal_factor()
        return CSMStoredSignalProvider(self.factory, factor.id).value(entity_id, session)


class CSMStoredSignalProvider:
    """The probability the trading cycle stored for (entity, session)."""

    def __init__(self, factory=None, factor_id: Optional[int] = None):
        self.factory = factory
        self.factor_id = factor_id

    def value(self, entity_id: int, session) -> Optional[float]:
        if self.factory is None or self.factor_id is None:
            return None
        d = _date_key(session).strftime("%Y-%m-%d %H:%M:%S")
        stored = self.factory.factor_value_local_repo.get_by_factor_entity_date(
            int(self.factor_id), int(entity_id), d, ENTITY_TYPE)
        try:
            return float(stored.value) if stored is not None else None
        except (TypeError, ValueError):
            return None

    def predict(self, dependencies: dict, entity, target_date) -> Optional[float]:
        if entity is None or getattr(entity, "id", None) is None:
            return None
        return self.value(int(entity.id), target_date)
