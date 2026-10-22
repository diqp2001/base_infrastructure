"""
LightGBM classifier of the cross-sectional momentum strategy, with the feature subset and the hyper-parameters
chosen by an Optuna study using the Tree-structured Parzen Estimator (TPE) sampler.

optimize(dataset, dates, cfg):
    * the training dates (rolling window known at the decision) are cut into n_folds + 1 consecutive blocks;
      fold k trains on blocks 0..k-1 and validates on block k (walk-forward), the last ``horizon`` training
      dates are PURGED because their labels are realised inside the validation block;
    * every trial switches each candidate feature on / off (``use__<feature>``) and draws the LightGBM
      hyper-parameters; trials with fewer than ``min_features`` features are pruned;
    * objective (maximised) = validation AUC (or the Sharpe of the daily top-minus-bottom quantile spread)
      averaged over the folds;
    * the best trial gives the features + parameters; the final model is refit on the whole window.

The study's own outputs are kept for the report: every trial's value, how often each feature was selected by the
best trials (selection frequency) and Optuna's hyper-parameter importances.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import CSMDataset

logger = logging.getLogger(__name__)


@dataclass
class StudyResult:
    features: List[str]
    params: Dict[str, Any]
    best_value: float
    fold_values: List[float]
    trial_values: List[Optional[float]]           # per trial, None when pruned / failed
    selection_frequency: Dict[str, float]         # feature -> share of the top trials that selected it
    param_importance: Dict[str, float] = field(default_factory=dict)
    n_trials: int = 0
    n_pruned: int = 0


@dataclass
class FittedModel:
    booster: Any                                  # lightgbm.Booster
    features: List[str]
    params: Dict[str, Any]
    study: StudyResult
    n_train_rows: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp                       # last date whose label was known

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.booster.predict(X[self.features].to_numpy(dtype=float))

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """TreeSHAP contributions [rows, features] (LightGBM pred_contrib, bias column dropped)."""
        return self.booster.predict(X[self.features].to_numpy(dtype=float), pred_contrib=True)[:, :-1]

    def gain_importance(self) -> Dict[str, float]:
        gain = self.booster.feature_importance(importance_type="gain")
        total = float(np.sum(gain)) or 1.0
        return {f: float(g) / total for f, g in zip(self.features, gain)}


# ---------------------------------------------------------------------------
# Folds and scoring
# ---------------------------------------------------------------------------

def walk_forward_folds(dates: List[pd.Timestamp], n_folds: int, purge: int) -> List[Tuple[list, list]]:
    """[(train dates, validation dates)]: expanding train, consecutive validation blocks, purged boundary."""
    dates = sorted(dates)
    blocks = np.array_split(np.arange(len(dates)), n_folds + 1)
    folds = []
    for k in range(1, n_folds + 1):
        train_idx = np.concatenate(blocks[:k])
        if purge:
            train_idx = train_idx[:-purge] if len(train_idx) > purge else train_idx[:0]
        valid_idx = blocks[k]
        if len(train_idx) and len(valid_idx):
            folds.append(([dates[i] for i in train_idx], [dates[i] for i in valid_idx]))
    return folds


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, p))


def long_short_sharpe(frame: pd.DataFrame, p: np.ndarray, quantile: float) -> float:
    """Annualised Sharpe of the daily equal-weight top-minus-bottom quantile forward return."""
    df = pd.DataFrame({"p": p, "r": frame["fwd_return"].to_numpy()},
                      index=frame.index.get_level_values("date"))
    spreads = []
    for _, g in df.groupby(level=0):
        if len(g) < 4:
            continue
        lo, hi = g["p"].quantile(quantile), g["p"].quantile(1 - quantile)
        top, bottom = g[g["p"] >= hi]["r"], g[g["p"] <= lo]["r"]
        if len(top) and len(bottom):
            spreads.append(top.mean() - bottom.mean())
    s = np.asarray(spreads)
    if len(s) < 2 or s.std(ddof=1) == 0:
        return float("nan")
    return float(s.mean() / s.std(ddof=1) * np.sqrt(252))


def _lgbm_params(params: Dict[str, Any], cfg: CSMConfiguration) -> Dict[str, Any]:
    p = dict(params)
    p.update(objective="binary", verbosity=-1, random_state=cfg.optimization.seed, n_jobs=cfg.optimization.n_jobs,
             subsample_freq=1 if p.get("subsample", 1.0) < 1.0 else 0)
    return p


def _fit(train: pd.DataFrame, features: List[str], params: Dict[str, Any], cfg: CSMConfiguration):
    import lightgbm as lgb
    model = lgb.LGBMClassifier(**_lgbm_params(params, cfg))
    model.fit(train[features].to_numpy(dtype=float), train["label"].to_numpy(dtype=int))
    return model.booster_


def _score(valid: pd.DataFrame, p: np.ndarray, cfg: CSMConfiguration) -> float:
    if cfg.optimization.metric == "long_short_sharpe":
        return long_short_sharpe(valid, p, cfg.training.long_short_quantile)
    return _auc(valid["label"].to_numpy(dtype=int), p)


# ---------------------------------------------------------------------------
# Optuna TPE study
# ---------------------------------------------------------------------------

def _suggest(trial, candidates: List[str], cfg: CSMConfiguration) -> Tuple[List[str], Dict[str, Any]]:
    o = cfg.optimization
    chosen = [f for f in candidates if trial.suggest_categorical(f"use__{f}", [True, False])]
    params = {
        "num_leaves": trial.suggest_int("num_leaves", *o.num_leaves),
        "max_depth": trial.suggest_int("max_depth", *o.max_depth),
        "learning_rate": trial.suggest_float("learning_rate", *o.learning_rate, log=True),
        "n_estimators": trial.suggest_int("n_estimators", *o.n_estimators),
        "min_child_samples": trial.suggest_int("min_child_samples", *o.min_child_samples),
        "subsample": trial.suggest_float("subsample", *o.subsample),
        "colsample_bytree": trial.suggest_float("colsample_bytree", *o.colsample_bytree),
        "reg_lambda": trial.suggest_float("reg_lambda", *o.reg_lambda, log=True),
    }
    return chosen, params


def optimize(dataset: CSMDataset, train_dates: List[pd.Timestamp], cfg: CSMConfiguration,
             log: Optional[Callable[[str], None]] = None) -> StudyResult:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    log = log or (lambda m: None)
    o = cfg.optimization
    candidates = list(dataset.feature_names)
    frame = dataset.frame
    rows = frame[frame.index.get_level_values("date").isin(train_dates) & frame["label"].notna()]
    folds = walk_forward_folds(sorted(set(rows.index.get_level_values("date"))), o.n_folds, cfg.label.horizon)
    if not folds:
        raise ValueError("Not enough labelled dates for the walk-forward folds")
    fold_frames = []
    for tr, va in folds:
        d = rows.index.get_level_values("date")
        fold_frames.append((rows[d.isin(tr)], rows[d.isin(va)]))

    def objective(trial):
        chosen, params = _suggest(trial, candidates, cfg)
        if len(chosen) < o.min_features:
            raise optuna.TrialPruned(f"{len(chosen)} features < {o.min_features}")
        scores = []
        for train, valid in fold_frames:
            tr, va = train.dropna(subset=chosen), valid.dropna(subset=chosen)
            if len(tr) < 50 or len(va) < 10 or tr["label"].nunique() < 2:
                continue
            booster = _fit(tr, chosen, params, cfg)
            scores.append(_score(va, booster.predict(va[chosen].to_numpy(dtype=float)), cfg))
            trial.report(float(np.nanmean(scores)), len(scores) - 1)
        scores = [s for s in scores if np.isfinite(s)]
        if not scores:
            raise optuna.TrialPruned("no fold could be scored")
        trial.set_user_attr("fold_values", scores)
        return float(np.mean(scores))

    with warnings.catch_warnings():               # multivariate / group TPE are flagged experimental by Optuna
        warnings.simplefilter("ignore", optuna.exceptions.ExperimentalWarning)
        sampler = optuna.samplers.TPESampler(seed=o.seed, n_startup_trials=o.n_startup_trials,
                                             multivariate=o.multivariate, group=o.multivariate)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(objective, n_trials=o.n_trials, timeout=o.timeout_seconds, catch=(ValueError,))

    complete = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    if not complete:
        raise RuntimeError("Optuna study produced no complete trial")
    best = study.best_trial
    top = sorted(complete, key=lambda t: t.value, reverse=True)[:max(1, int(round(len(complete) * o.top_trial_fraction)))]
    frequency = {f: float(np.mean([bool(t.params.get(f"use__{f}")) for t in top])) for f in candidates}
    try:
        importance = optuna.importance.get_param_importances(
            study, params=[k for k in best.params if not k.startswith("use__")])
    except Exception as e:                       # needs >1 distinct value per parameter
        logger.debug(f"param importances unavailable: {e}")
        importance = {}
    result = StudyResult(
        features=[f for f in candidates if best.params.get(f"use__{f}")],
        params={k: v for k, v in best.params.items() if not k.startswith("use__")},
        best_value=float(best.value),
        fold_values=list(best.user_attrs.get("fold_values", [])),
        trial_values=[t.value if t.state == optuna.trial.TrialState.COMPLETE else None for t in study.trials],
        selection_frequency=frequency,
        param_importance={k: float(v) for k, v in importance.items()},
        n_trials=len(study.trials),
        n_pruned=sum(1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED),
    )
    log(f"[CSM] Optuna TPE: {result.n_trials} trials ({result.n_pruned} pruned), best "
        f"{cfg.optimization.metric}={result.best_value:.4f} with {len(result.features)} features")
    return result


def train(dataset: CSMDataset, train_dates: List[pd.Timestamp], cfg: CSMConfiguration,
          log: Optional[Callable[[str], None]] = None) -> FittedModel:
    """Optuna TPE study on the window, then the final model on every labelled row of the window."""
    study = optimize(dataset, train_dates, cfg, log=log)
    frame = dataset.frame
    rows = frame[frame.index.get_level_values("date").isin(train_dates)].dropna(subset=study.features + ["label"])
    booster = _fit(rows, study.features, study.params, cfg)
    dates = rows.index.get_level_values("date")
    return FittedModel(booster=booster, features=study.features, params=study.params, study=study,
                       n_train_rows=len(rows), train_start=dates.min(), train_end=dates.max())
