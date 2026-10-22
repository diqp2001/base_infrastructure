"""
CSMModelProvider — injected into CompanyShareCrossSectionalMomentumFactor by its repository (the counterpart of
LGBMMomentumModelProvider for the quintile-rank factor).

predict(dependencies, entity, target_date):
    1. the probability the trading cycle stored for (entity, session), when there is one;
    2. otherwise the model valid at the date (CSMArtifactStore.select: trained as of a session <= date) applied to
       the resolved candidate features: CSMFeatureDefinition.extract builds the 35-feature vector from
       the dependency values, the model reads the subset Optuna selected. A model that selected cross-sectional
       ranks needs the whole cross-section and cannot score one entity alone -> None.

No model is trained here: training happens in the trading cycle, on data known at its session.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_artifact_store import (
    CSMArtifactStore,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_signal_store import (
    CSMStoredSignalProvider,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
    CSMFeatureDefinition,
)


class CSMModelProvider:
    # set by the project's model trainer, so repository-injected providers use the project configuration
    default_config: Optional[CSMConfiguration] = None

    def __init__(self, factory=None, factor_id: Optional[int] = None, config: Optional[CSMConfiguration] = None):
        self.factory = factory
        self.factor_id = factor_id
        self.config = config or CSMModelProvider.default_config or CSMConfiguration()
        self.feature_def = CSMFeatureDefinition()
        self._loaded = {}

    def stored(self, entity_id: int, target_date) -> Optional[float]:
        return CSMStoredSignalProvider(self.factory, self.factor_id).value(entity_id, target_date)

    def predict(self, dependencies: dict, entity, target_date) -> Optional[float]:
        if entity is None or getattr(entity, "id", None) is None or self.factory is None:
            return None
        value = self.stored(int(entity.id), target_date)
        if value is not None:
            return value
        vector = self.feature_def.extract(dependencies, entity, target_date)
        if vector is None:
            return None
        store = CSMArtifactStore(self.factory, self.config)
        selected = store.select(pd.Timestamp(target_date))
        if selected is None:
            return None
        artifact = selected[0]
        if artifact.id not in self._loaded:
            self._loaded[artifact.id] = store.load(artifact)
        model = self._loaded[artifact.id]
        row = pd.DataFrame([vector], columns=self.feature_def.FEATURE_NAMES)
        if any(f not in row.columns for f in model.features):
            return None                                        # cross-sectional ranks: not computable alone
        p = float(model.predict_proba(row)[0])
        return p if np.isfinite(p) else None
