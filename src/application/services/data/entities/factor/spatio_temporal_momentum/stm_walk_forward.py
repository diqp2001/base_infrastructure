"""
STMWalkForwardTrainer — the reference expanding-window experiment
(train_multivariate.ipynb cell 19) as a reusable service.

For every split start S (yearly):
    train <= S < val <= S+val < test <= S+val+test
    fit -> best checkpoint on validation Sharpe -> predict val and test
Test predictions of consecutive windows form the out-of-sample signal
history used by the backtest.  When a RepositoryFactory is supplied each
window is persisted as ModelTraining + TrainingMetric + ModelArtifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    STMArtifactStore,
    build_artifact_metadata,
    rebuild_model,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
    evaluate_with_baselines,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    FeaturePanel,
    SampleSet,
    make_split,
    walk_forward_starts,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_metrics import hit_rate
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_feature_store import (
    STMFeatureStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_models import build_model
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_training import (
    predict_last_step,
    train_window,
)


@dataclass
class WindowResult:
    start: pd.Timestamp
    val_preds: np.ndarray
    test_preds: np.ndarray
    val: SampleSet
    test: SampleSet
    evaluation: Dict[str, Dict[str, object]]
    best_val_sharpe: float
    best_epoch: Optional[int]
    epochs_run: int
    training_id: Optional[int] = None
    artifact_id: Optional[int] = None
    metadata: Dict[str, object] = field(default_factory=dict)


class STMWalkForwardTrainer:

    def __init__(self, config: STMConfiguration, factory=None, log: Optional[Callable[[str], None]] = None):
        self.config = config
        self.factory = factory
        self.log = log or (lambda msg: None)
        self.artifact_store = STMArtifactStore(factory, config) if factory is not None else None

    def _prepare_persistence(self, feature_factor_ids, signal_factor_id):
        if self.artifact_store is None:
            return None
        store = STMFeatureStore(self.factory, self.config)
        if not feature_factor_ids:
            feature_factor_ids = store.ensure_feature_factors()
        if signal_factor_id is None:
            signal_factor_id = store.ensure_signal_factor().id
        ml_model = self.artifact_store.ensure_ml_model(target_factor_id=signal_factor_id)
        self.artifact_store.ensure_model_features(ml_model, feature_factor_ids)
        return ml_model

    def _train_split(self, panel: FeaturePanel, split, start, ml_model, asset_entity_ids, universe_id,
                     valid_until=None) -> WindowResult:
        cfg = self.config
        n_assets, n_features = len(panel.assets), len(panel.feature_names)
        training = None
        if self.artifact_store is not None:
            training = self.artifact_store.start_training(ml_model, universe_id, split,
                                                          first_train_date=split.train.dates[0])
        try:
            res = train_window(lambda: build_model(n_assets, n_features, cfg.model),
                               split.train, split.val, cfg.training, log=self.log)
        except Exception:
            if training is not None:
                self.artifact_store.finish_training(training, ok=False)
            raise

        metadata = build_artifact_metadata(cfg, panel.assets, asset_entity_ids, panel.feature_names,
                                           split, split.scaler, universe_id, res,
                                           history_start=panel.dates[0], valid_until=valid_until)
        model = rebuild_model(metadata, res.state_dict)
        val_preds = predict_last_step(model, split.val, cfg.training.batch_size)
        test_preds = predict_last_step(model, split.test, cfg.training.batch_size)
        evaluation = (evaluate_with_baselines(test_preds, split.test, panel.feature_names,
                                              cfg.training.basis_points, cfg.training.target_vol,
                                              model_name=f"stm_{cfg.model.model_type}")
                      if len(split.test) else {})
        wr = WindowResult(start=start, val_preds=val_preds, test_preds=test_preds, val=split.val,
                          test=split.test, evaluation=evaluation, best_val_sharpe=res.best_val_sharpe,
                          best_epoch=res.best_epoch, epochs_run=res.epochs_run, metadata=metadata)
        if training is not None:
            artifact = self.artifact_store.save_artifact(training, model, metadata)
            self.artifact_store.record_metrics(
                training, self._metrics(wr),
                calculation_date=split.test_end if len(split.test) else split.val_end)
            self.artifact_store.finish_training(training, ok=True)
            wr.training_id, wr.artifact_id = training.id, artifact.id
        return wr

    def run(self, panel: FeaturePanel, asset_entity_ids: Optional[Dict[str, int]] = None,
            universe_id: Optional[int] = None, feature_factor_ids: Optional[Dict[str, int]] = None,
            signal_factor_id: Optional[int] = None) -> List[WindowResult]:
        """Research mode: every walk-forward window of the configuration (reference notebook)."""
        cfg = self.config
        ml_model = self._prepare_persistence(feature_factor_ids, signal_factor_id)
        results: List[WindowResult] = []
        for start in walk_forward_starts(cfg.training):
            split = make_split(panel, start, cfg)
            if len(split.train) == 0 or len(split.val) == 0 or len(split.test) == 0:
                self.log(f"[STM] window {start.date()}: skipped (train={len(split.train)}, "
                         f"val={len(split.val)}, test={len(split.test)})")
                continue
            self.log(f"[STM] window {start.date()}: train={len(split.train)} val={len(split.val)} "
                     f"test={len(split.test)}")
            results.append(self._train_split(panel, split, start, ml_model, asset_entity_ids or {}, universe_id))
        return results

    def train_as_of(self, panel: FeaturePanel, as_of, asset_entity_ids: Optional[Dict[str, int]] = None,
                    universe_id: Optional[int] = None, valid_days: int = 365,
                    feature_factor_ids: Optional[Dict[str, int]] = None,
                    signal_factor_id: Optional[int] = None) -> Optional[WindowResult]:
        """
        Time-driven (backtest and live) mode: train at decision date ``as_of``
        with what is known then.
            train       <= as_of - val_days (purged)
            validation  (as_of - val_days, as_of]
            no test fold: the future is the test.
        The artifact is valid from the next session for ``valid_days``.
        ``panel`` must only contain data available at ``as_of`` (frontier reader).
        """
        cfg = self.config
        as_of = bar_key(as_of, cfg.bar_minutes)
        if len(panel.dates) and panel.dates[-1] > as_of:
            raise ValueError(f"Panel extends past the decision date {as_of.date()} (look-ahead)")
        start = as_of - pd.Timedelta(days=cfg.training.val_days)
        split = make_split(panel, start, cfg, test_days=0)
        if len(split.train) == 0 or len(split.val) == 0:
            self.log(f"[STM] train_as_of {as_of.date()}: not enough data "
                     f"(train={len(split.train)}, val={len(split.val)})")
            return None
        self.log(f"[STM] train_as_of {as_of.date()}: train={len(split.train)} val={len(split.val)}")
        ml_model = self._prepare_persistence(feature_factor_ids, signal_factor_id)
        return self._train_split(panel, split, start, ml_model, asset_entity_ids or {}, universe_id,
                                 valid_until=as_of + pd.Timedelta(days=valid_days))

    def _metrics(self, wr: WindowResult) -> Dict[str, Dict[str, float]]:
        model_key = f"stm_{self.config.model.model_type}"
        metrics = {
            "training": {"epochs_run": wr.epochs_run,
                         "best_epoch": wr.best_epoch if wr.best_epoch is not None else float("nan")},
            "validation": {"sharpe_0bps": wr.best_val_sharpe, "sample_count": len(wr.val),
                           "hit_rate": hit_rate(wr.val.y[:, -1, :], wr.val_preds) if len(wr.val) else float("nan")},
        }
        test_eval = wr.evaluation.get(model_key)
        if not test_eval:          # time-driven training: no test fold
            return metrics
        metrics["test"] = {"sample_count": len(wr.test), "hit_rate": test_eval["hit_rate"]}
        for c, stats in test_eval["by_cost"].items():
            for name in ("sharpe_ratio", "sortino_ratio", "calmar_ratio", "max_drawdown", "annual_return"):
                metrics["test"][f"{name}_{c}bps"] = stats[name]
        return metrics


def out_of_sample_signals(results: List[WindowResult]) -> pd.DataFrame:
    """Concatenate test-window predictions into one date x asset signal frame (no overlap)."""
    frames = []
    for wr in results:
        assets = wr.metadata.get("assets")
        frames.append(pd.DataFrame(wr.test_preds, index=wr.test.dates, columns=assets))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames)
    return out[~out.index.duplicated(keep="last")].sort_index()
