"""
Monthly walk-forward classifier backtest — the four CompanyShare stock-ranking models on one shared monthly setup,
for the classifier evaluation (/powerbuffet/model-evaluation). Model evaluation only: no TradingStrategy, no engine.

Setup (owner's choices, 2026-11-23):
    universe    DJIA point-in-time members (djia_membership: members in force at each month end, from 2020-08-31);
                training rows before 2020-08-31 use the base members' own history (survivors), as the STM decile
                project does — predictions are only made from 2021, on the members in force
    prices      dividend- and split-adjusted daily closes of the members (the cached IBKR files of the ETF
                dispersion / STM decile projects, Eulerpool fallback), from 2007
    dates       T = the last trading day of every month, predictions from START to END (Jan 2021 .. Oct 2026)
    target      the NEXT MONTH: forward return = close at the next month end / close at T - 1;
                5 classes = per-date quintile of that return (1 = worst .. 5 = best, the LGBM trainer's ordinal rule);
                2 classes = above the date's cross-sectional median (the CSM rule)
    training    at T, every model is fit on month-end rows dated BEFORE T (their next-month label is realised at T at
                the latest), over a rolling window; retrained every month; nothing after T is read

Models (each keeps its own algorithm; only the target / frequency are the shared monthly ones):
    csm             CSM LightGBM binary classifier, features + hyper-parameters by Optuna TPE (csm_model.train), on
                    the CSM candidate features (the 24 momentum factors + extras, CSMFeatureEngine, daily closes)
    lgbm_quintile   LGBM quintile classifier (lgb.LGBMClassifier with LGBMMomentumModelConfiguration's parameters) on the
                    24 momentum features, 5 classes
    random_forest   the test_base_project RandomForest (100 trees, random_state 42) ported: its features (two lagged
                    returns + volatility) on monthly bars, one model pooled over the members, binary target
    stm             the STM model (STMConstituentScorer, the STM decile project's model A configuration): a score in
                    [-1, 1], evaluated as a ranking (score quintiles), no class probabilities

Outputs: results/classifier_backtests/<stamp>/<model>.csv (the observation table) and manifest.json, read by
ClassifierBacktestFileSource. Run:  python -m src.application.services.model_evaluation.monthly_classifier_backtest
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.application.services.model_evaluation.observations import (
    cross_sectional_classes,
    median_split_classes,
    predicted_classes,
    probability_columns,
)

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[4]
RESULTS_DIR = ROOT / "results" / "classifier_backtests"
PRICE_DIR = ROOT / "results" / "etf_dispersion_stm" / "price_history"
MODELS = ("csm", "lgbm_quintile", "random_forest", "stm")


@dataclass
class MonthlyBacktestConfig:
    start: str = "2021-01-01"                  # first prediction month end on or after
    end: str = "2026-10-31"
    history_start: str = "2007-01-01"
    training_window_months: int = 120          # rolling window of month-end rows
    min_training_months: int = 24
    retrain_every_months: int = 1
    n_quantiles: int = 5
    csm_trials: int = 25
    models: Sequence[str] = MODELS
    price_dir: str = str(PRICE_DIR)


# ── data ────────────────────────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class MonthlyData:
    closes: pd.DataFrame                       # daily adjusted closes, one column per symbol
    month_ends: pd.DatetimeIndex               # last trading day of every month (all history)
    members_at: Callable[[date], List[str]]
    sources: Dict[str, str] = field(default_factory=dict)      # symbol -> price source used

    def monthly(self) -> pd.DataFrame:
        return self.closes.loc[self.month_ends]

    def forward_returns(self) -> pd.DataFrame:
        """At each month end T: close(next month end) / close(T) - 1 (NaN at the last month end)."""
        m = self.monthly()
        return m.shift(-1) / m - 1.0


def load_djia_data(cfg: MonthlyBacktestConfig) -> MonthlyData:
    from src.application.services.data.backtest_preload.daily_price_sources import CacheFileReader, PreferredPrices
    from src.application.services.universe.djia_membership import BASE_MEMBERS, build_membership
    membership = build_membership()

    def members_at(day: date) -> List[str]:
        # point in time from the base date; before it (training history only, never a prediction date) the base
        # members, as the STM decile project trains on its members' own history
        return membership.members_at(day) if day >= membership.base_date else list(BASE_MEMBERS)

    prices = PreferredPrices([("ibkr", CacheFileReader(os.path.join(cfg.price_dir, "ibkr"))),
                              ("eulerpool", CacheFileReader(os.path.join(cfg.price_dir, "eulerpool")))])
    start, end = date.fromisoformat(cfg.history_start), date.fromisoformat(cfg.end)
    series = {}
    for symbol in membership.all_constituents():
        closes = prices.daily_closes(_underlying(symbol), start, max(end, date.today()))
        if closes:
            series[symbol] = pd.Series(closes, dtype=float)
    closes = pd.DataFrame(series).sort_index()
    closes.index = pd.DatetimeIndex(closes.index)
    days = closes.index[closes.notna().any(axis=1)]
    month_ends = pd.DatetimeIndex(days.to_series().groupby(days.to_period("M")).max().to_numpy())
    return MonthlyData(closes=closes, month_ends=month_ends, members_at=members_at, sources=dict(prices.served))


def _underlying(symbol: str):
    from types import SimpleNamespace
    return SimpleNamespace(symbol=symbol)                     # the cache readers only read the symbol


# ── features (known at T) ───────────────────────────────────────────────────────────────────────────────────────

def momentum_features(data: MonthlyData, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """CSM candidate features (24 momentum factors + extras, the domain factors' calculate()) of every symbol at each
    month end, from the daily closes dated <= that month end. MultiIndex (date, asset)."""
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
        CSMFeatureConfig,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import CSMFeatureEngine
    engine = CSMFeatureEngine(CSMFeatureConfig())
    frames = []
    for symbol in data.closes.columns:
        f = engine.features_at(symbol, data.closes[symbol].dropna(), dates)
        if not f.empty:
            f.index = pd.MultiIndex.from_product([f.index, [symbol]], names=["date", "asset"])
            frames.append(f)
    return pd.concat(frames).sort_index()


def random_forest_features(data: MonthlyData) -> pd.DataFrame:
    """test_base_project's RandomForest inputs on monthly bars: last month's and the previous month's return, and the
    volatility of the daily returns over the last month (all known at T)."""
    m = data.monthly()
    r = m / m.shift(1) - 1.0
    daily = data.closes.pct_change(fill_method=None)
    vol = daily.groupby(daily.index.to_period("M")).std()
    month_end = {me.to_period("M"): me for me in data.month_ends}
    vol.index = pd.DatetimeIndex([month_end[p] for p in vol.index])
    out = pd.concat({"return_lag1": r.stack(), "return_lag2": r.shift(1).stack(),
                     "volatility": vol.reindex(m.index).stack()}, axis=1)
    out.index = out.index.set_names(["date", "asset"])
    return out


# ── models: fit on rows dated before T, predict the members at T ───────────────────────────────────────────────

class _Tabular:
    classes: List[int] = []
    features: List[str] = []

    def fit(self, rows: pd.DataFrame, y: pd.Series):
        raise NotImplementedError

    def predict_proba(self, rows: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError


class CSMClassifier(_Tabular):
    classes = [0, 1]

    def __init__(self, n_trials: int):
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
            CSMConfiguration,
            CSMLabelConfig,
            CSMOptimizationConfig,
        )
        self.cfg = CSMConfiguration(label=CSMLabelConfig(horizon=1),          # 1 row = 1 month: purge one row
                                    optimization=CSMOptimizationConfig(n_trials=n_trials, n_startup_trials=8))
        self.model = None
        self.features = []                    # chosen by the Optuna study; LightGBM reads missing values

    def fit(self, rows, y):
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import CSMDataset
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_model import train
        frame = rows.copy()
        names = list(rows.columns)
        frame["label"] = y
        frame["fwd_return"] = np.nan
        frame["daily_vol"] = np.nan
        dataset = CSMDataset(frame=frame, feature_names=names)
        self.model = train(dataset, sorted(set(frame.index.get_level_values("date"))), self.cfg)

    def predict_proba(self, rows):
        p1 = np.asarray(self.model.predict_proba(rows), dtype=float)
        return np.column_stack([1.0 - p1, p1])


class LGBMQuintileClassifier(_Tabular):
    classes = [1, 2, 3, 4, 5]

    def __init__(self):
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_configuration import (
            LGBMMomentumModelConfiguration,
        )
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
            LGBMMomentumFeatureDefinition,
        )
        self.config = LGBMMomentumModelConfiguration()
        self.features = list(LGBMMomentumFeatureDefinition.FEATURE_NAMES)
        self.model = None

    def fit(self, rows, y):
        import lightgbm as lgb
        c = self.config
        ok = rows[self.features].notna().all(axis=1)              # the trainer keeps samples with all 24 features
        self.model = lgb.LGBMClassifier(n_estimators=c.n_estimators, max_depth=c.max_depth,
                                        learning_rate=c.learning_rate, num_leaves=c.num_leaves,
                                        min_child_samples=c.min_data_in_leaf, random_state=c.random_state,
                                        n_jobs=-1, verbose=-1)
        self.model.fit(rows.loc[ok, self.features].to_numpy(dtype=float), y[ok].astype(int).to_numpy())

    def predict_proba(self, rows):
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_model_provider import (
            class_probabilities,
        )
        labels, p = class_probabilities(self.model, rows[self.features].to_numpy(dtype=float))
        return _aligned(labels, p, self.classes)


class RandomForestPort(_Tabular):
    classes = [0, 1]
    features = ["return_lag1", "return_lag2", "volatility"]

    def __init__(self):
        self.model = None

    def fit(self, rows, y):
        from sklearn.ensemble import RandomForestClassifier
        ok = rows[self.features].notna().all(axis=1)
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(rows.loc[ok, self.features].to_numpy(dtype=float), y[ok].astype(int).to_numpy())

    def predict_proba(self, rows):
        p = self.model.predict_proba(rows[self.features].to_numpy(dtype=float))
        return _aligned([int(k) for k in self.model.classes_], p, self.classes)


def _aligned(labels: List[int], p: np.ndarray, classes: List[int]) -> np.ndarray:
    """Probability columns in the model's class order; a class absent from the training labels gets 0."""
    out = np.zeros((len(p), len(classes)))
    for j, k in enumerate(classes):
        if k in labels:
            out[:, j] = p[:, labels.index(k)]
    return out


# ── the walk-forward loop ───────────────────────────────────────────────────────────────────────────────────────

def decision_dates(data: MonthlyData, cfg: MonthlyBacktestConfig) -> pd.DatetimeIndex:
    me = data.month_ends
    return me[(me >= pd.Timestamp(cfg.start)) & (me <= pd.Timestamp(cfg.end))]


def true_classes(fwd: pd.DataFrame, members_at, n: int) -> pd.DataFrame:
    """Long table (date, asset, forward_return, true_5, true_2) over each date's members with a forward return."""
    rows = []
    for t in fwd.index:
        for s in members_at(t.date()):
            if s in fwd.columns and np.isfinite(fwd.at[t, s]):
                rows.append({"date": t, "asset": s, "forward_return": float(fwd.at[t, s])})
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    long["true_5"] = cross_sectional_classes(long, "forward_return", n)
    long["true_2"] = median_split_classes(long, "forward_return")
    return long


def walk_forward(model_factory: Callable[[], _Tabular], features: pd.DataFrame, labels: pd.DataFrame,
                 target: str, dates: pd.DatetimeIndex, members_at, cfg: MonthlyBacktestConfig,
                 log=None) -> pd.DataFrame:
    """Out-of-sample probabilities at each T from a model fit on rows dated < T (their label realised by T)."""
    log = log or logger.info
    lab = labels.set_index(["date", "asset"])
    table = features.join(lab[[target]], how="inner")                       # rows of members (labels are)
    feats = [c for c in features.columns]
    out = []
    model, trained_at = None, None
    all_dates = sorted(set(features.index.get_level_values("date")))
    for i, t in enumerate(dates):
        past = [d for d in all_dates if d < t][-cfg.training_window_months:]
        train = table[table.index.get_level_values("date").isin(past)].dropna(subset=[target])
        if train.index.get_level_values("date").nunique() < cfg.min_training_months:
            continue
        if model is None or i % cfg.retrain_every_months == 0:
            model = model_factory()
            model.fit(train[feats], train[target])
            trained_at = t
        members = set(members_at(t.date()))
        now = features[(features.index.get_level_values("date") == t)
                       & features.index.get_level_values("asset").isin(members)]
        if model.features and not isinstance(model, CSMClassifier):
            now = now.dropna(subset=model.features)
        if now.empty:
            continue
        p = model.predict_proba(now[feats])
        block = pd.DataFrame(p, columns=probability_columns(model.classes), index=now.index).reset_index()
        block["run_id"] = int(trained_at.strftime("%Y%m"))
        out.append(block)
        log(f"  {t.date()}: {len(block)} predictions (model trained {trained_at.date()} on {len(train)} rows)")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def stm_scores(data: MonthlyData, dates: pd.DatetimeIndex, log=None) -> pd.DataFrame:
    """STM model A of the decile project, retrained every month, scoring the members at each T."""
    from src.application.managers.project_managers.stm_monthly_decile_project import config as decile_config
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import (
        STMConstituentScorer,
    )
    from src.application.services.portfolio_research.stm_decile_cycle import period_end_panel
    log = log or logger.info
    scorer = STMConstituentScorer(decile_config.build_stm_configuration(), 1, log=log)
    rows = []
    for t in dates:
        members = [s for s in data.members_at(t.date()) if s in data.closes.columns]
        panel = period_end_panel(data.closes[members], t, "M")
        scores = scorer.score(panel, members, t)
        for s, v in scores.scores.items():
            rows.append({"date": t, "asset": s, "score": float(v),
                         "run_id": int(pd.Timestamp(scores.trained_at or t).strftime("%Y%m"))})
        log(f"  {t.date()}: STM scored {len(scores.scores)} members ({len(scores.unscored)} unscored)")
    return pd.DataFrame(rows)


def observations(pred: pd.DataFrame, labels: pd.DataFrame, classes: List[int], true_column: str) -> pd.DataFrame:
    """The observation table of ClassifierObservationSourcePort."""
    obs = pred.merge(labels[["date", "asset", "forward_return", true_column]], on=["date", "asset"], how="left")
    obs = obs.rename(columns={true_column: "true_class"})
    obs["symbol"] = obs["asset"]
    if "score" in obs.columns:                      # a ranking model: the predicted class = its score quintile
        obs["predicted_class"] = cross_sectional_classes(obs, "score", len(classes))
    else:
        obs["predicted_class"] = predicted_classes(obs[probability_columns(classes)].to_numpy(), classes)
    return obs.sort_values(["date", "asset"]).reset_index(drop=True)


MODEL_INFO = {
    "csm": dict(name="CSM LightGBM + Optuna TPE (binary)", classes=[0, 1], true="true_2", output="probabilities",
                definition="1 when the next-month return is above the date's cross-sectional median of the members"),
    "lgbm_quintile": dict(name="LGBM momentum quintile (5 classes)", classes=[1, 2, 3, 4, 5], true="true_5",
                          output="probabilities",
                          definition="per-date quintile of the next-month return (1 = worst .. 5 = best)"),
    "random_forest": dict(name="RandomForest (test_base_project port, binary)", classes=[0, 1], true="true_2",
                          output="probabilities",
                          definition="1 when the next-month return is above the date's cross-sectional median"),
    "stm": dict(name="STM (spatio-temporal momentum, score ranking)", classes=[1, 2, 3, 4, 5], true="true_5",
                output="score",
                definition="per-date quintile of the next-month return; predicted class = per-date STM score quintile"),
}


def run(cfg: MonthlyBacktestConfig, out_dir: Optional[Path] = None, data: Optional[MonthlyData] = None,
        log=None) -> Path:
    log = log or (lambda m: print(m, flush=True))
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out_dir = Path(out_dir or RESULTS_DIR / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = data or load_djia_data(cfg)
    dates = decision_dates(data, cfg)
    labels = true_classes(data.forward_returns(), data.members_at, cfg.n_quantiles)
    manifest = {"stamp": out_dir.name, "started_at": datetime.now().isoformat(timespec="seconds"),
                "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(cfg).items()},
                "universe": "DJIA point-in-time members (djia_membership, from 2020-08-31); training rows before "
                            "2020-08-31 use the base members' own history (survivors)",
                "prices": "adjusted daily closes (cached IBKR files, Eulerpool fallback)", "price_sources": data.sources,
                "decision_dates": [d.date().isoformat() for d in dates], "git_commit": _git_commit(), "models": {}}
    _write(out_dir / "manifest.json", manifest)
    features = None
    for name in cfg.models:
        info = MODEL_INFO[name]
        t0 = time.time()
        log(f"[{name}] {info['name']}")
        try:
            if name == "stm":
                pred = stm_scores(data, dates, log)
            else:
                if name in ("csm", "lgbm_quintile") and features is None:
                    log("  computing the momentum features at every month end ...")
                    features = momentum_features(data, data.month_ends[data.month_ends <= pd.Timestamp(cfg.end)])
                feats = random_forest_features(data) if name == "random_forest" else features
                if name == "lgbm_quintile":
                    feats = feats[LGBMQuintileClassifier().features]
                factory = {"csm": lambda: CSMClassifier(cfg.csm_trials), "lgbm_quintile": LGBMQuintileClassifier,
                           "random_forest": RandomForestPort}[name]
                pred = walk_forward(factory, feats, labels, info["true"], dates, data.members_at, cfg, log)
            obs = observations(pred, labels, info["classes"], info["true"])
            obs.to_csv(out_dir / f"{name}.csv", index=False)
            runs = sorted(int(r) for r in obs["run_id"].unique()) if len(obs) else []
            manifest["models"][name] = {**{k: v for k, v in info.items() if k != "true"}, "file": f"{name}.csv",
                                        "observations": int(len(obs)), "runs": runs, "status": "completed",
                                        "seconds": round(time.time() - t0, 1)}
        except Exception as e:                                       # one model failing never hides the others
            logger.exception(name)
            manifest["models"][name] = {**{k: v for k, v in info.items() if k != "true"}, "status": "failed",
                                        "error": repr(e), "seconds": round(time.time() - t0, 1)}
        _write(out_dir / "manifest.json", manifest)
        log(f"[{name}] {manifest['models'][name]['status']} in {manifest['models'][name]['seconds']} s")
    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    _write(out_dir / "manifest.json", manifest)
    return out_dir


def _write(path: Path, obj) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _git_commit() -> Optional[str]:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description="Monthly walk-forward backtest of the CompanyShare classifier models")
    p.add_argument("--start", default=MonthlyBacktestConfig.start)
    p.add_argument("--end", default=MonthlyBacktestConfig.end)
    p.add_argument("--models", default=",".join(MODELS))
    p.add_argument("--csm-trials", type=int, default=MonthlyBacktestConfig.csm_trials)
    a = p.parse_args(argv)
    cfg = MonthlyBacktestConfig(start=a.start, end=a.end, models=tuple(a.models.split(",")), csm_trials=a.csm_trials)
    print(run(cfg))


if __name__ == "__main__":
    main()
