"""
Monthly walk-forward backtest of the CSM LightGBM + Optuna TPE classifier on the S&P 500 (owner's choices,
2026-11-23), for the classifier evaluation (/powerbuffet/model-evaluation). Model evaluation only.

    universe    S&P 500 point-in-time members (sp500_membership: Wikipedia, rolled back from today to 2007)
    prices      Eulerpool daily OHLCV (split-adjusted, not dividend-adjusted: price returns), file caches
                (sp500_data); a member's month-end close = its last close within 5 sessions of the month end.
                Delisted companies are often missing from Eulerpool: the member-months without bars are left out
                (coverage in the manifest: ~77% of members in 2012, ~99% from 2022)
    candidates  the 48 CSM candidates + the 27 liquidity / volume factors (opt-in group) + the 5 share turnover
                factors (volume / shares outstanding, the balance sheet's latest published count) + the 75
                point-in-time fundamental candidates (Eulerpool statements, file cache) - the Optuna study keeps those
                present on enough rows (the SPY-relative and the hedging-band ones have no input here and drop out)
    target      next month: forward return above the date's cross-sectional median of the members (binary)
    dates       month ends 2012-01 .. 2026-10; each month the model is retrained on the month ends dated before it
                (rolling 120 months, at least 24), as the DJIA backtest (monthly_classifier_backtest)

Outputs: results/classifier_backtests/<stamp>/{manifest.json, csm.csv}, read by ClassifierBacktestFileSource.
Run:  python -m src.application.services.model_evaluation.sp500_monthly_backtest
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from src.application.services.model_evaluation import monthly_classifier_backtest as mcb
from src.application.services.model_evaluation import sp500_data

FILL_SESSIONS = 5                   # a month-end close may be the member's last close up to 5 sessions earlier


@dataclass
class SP500BacktestConfig:
    start: str = "2012-01-01"
    end: str = "2026-10-31"
    training_window_months: int = 120
    min_training_months: int = 24
    retrain_every_months: int = 1
    n_quantiles: int = 5
    csm_trials: int = 15
    fundamentals: bool = True
    liquidity_volume: bool = True
    turnover: bool = True


def load(cfg: SP500BacktestConfig, log=print):
    """(MonthlyData of month-end closes, raw bar panels, membership, symbols with bars)."""
    from src.application.services.universe import sp500_membership as spm
    snapshot = spm.load_snapshot()
    membership = snapshot.membership()
    symbols = spm.all_symbols(snapshot)
    panels = sp500_data.load_panels(symbols)
    closes = panels["close"]
    days = closes.index[closes.notna().sum(axis=1) >= 0.5 * closes.notna().sum(axis=1).max()]   # trading days
    closes = closes.loc[days]
    month_ends = pd.DatetimeIndex(days.to_series().groupby(days.to_period("M")).max().to_numpy())
    month_ends = month_ends[month_ends >= pd.Timestamp(membership.base_date)]

    def members_at(day: date) -> List[str]:
        return membership.members_at(max(day, membership.base_date))

    filled = closes.ffill(limit=FILL_SESSIONS)
    data = mcb.MonthlyData(closes=filled, month_ends=month_ends, members_at=members_at)
    log(f"S&P 500: {len(symbols)} symbols, {closes.shape[1]} with bars, {len(month_ends)} month ends "
        f"{month_ends[0].date()} .. {month_ends[-1].date()}")
    return data, panels, membership, list(closes.columns)


def bar_features(panels, symbols: List[str], month_ends: pd.DatetimeIndex, cfg: SP500BacktestConfig,
                 log=print) -> pd.DataFrame:
    """Bar candidates of every symbol at each month end, from its own bars dated <= its last session at or before
    the month end (within FILL_SESSIONS). MultiIndex (date = month end, asset)."""
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
        CSMFeatureConfig,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import CSMFeatureEngine
    engine = CSMFeatureEngine(CSMFeatureConfig(liquidity_volume=cfg.liquidity_volume))
    frames, t0 = [], time.time()
    for i, s in enumerate(symbols, 1):
        frame = pd.DataFrame({f: panels[f][s] for f in ("close", "volume", "high", "low") if s in panels[f]})
        frame = frame[frame["close"].notna()].sort_index()
        if frame.empty:
            continue
        pos = frame.index.searchsorted(month_ends, side="right") - 1
        mapping = {}
        for t, p in zip(month_ends, pos):
            if p >= 0 and (t - frame.index[p]).days <= FILL_SESSIONS + 4:
                mapping[frame.index[p]] = t
        if not mapping:
            continue
        f = engine.features_at(s, frame, list(mapping))
        f.index = pd.MultiIndex.from_arrays([[mapping[d] for d in f.index], [s] * len(f)], names=["date", "asset"])
        frames.append(f)
        if i % 100 == 0:
            log(f"  bar features: {i}/{len(symbols)} symbols ({time.time() - t0:.0f}s)")
    return pd.concat(frames).sort_index()


def turnover_features(panels, symbols: List[str], month_ends: pd.DatetimeIndex, log=print, sources=None,
                      errors=()) -> pd.DataFrame:
    """The share turnover factors (TURNOVER_FACTOR_CLASSES) at each month end, each by its own calculate(): the
    symbol's last volumes up to its last session at or before the month end (within FILL_SESSIONS) and the latest
    balance sheet share count published before the month end (point in time, the quarterly max_age)."""
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_fundamentals import (
        _policy,
        window_as_of,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_liquidity_volume_factors import (  # noqa: E501
        SHARES_OUTSTANDING,
        TURNOVER_FACTOR_CLASSES,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (  # noqa: E501
        BALANCE_SHEET,
        QUARTERLY,
    )
    if sources is None:
        sources, errors = sp500_data.statement_sources()
    errors = tuple(errors) or (RuntimeError,)
    factors = [cls() for cls in TURNOVER_FACTOR_CLASSES]
    policy = _policy(QUARTERLY)
    rows, t0 = [], time.time()
    for i, s in enumerate(symbols, 1):
        try:
            records = sources[BALANCE_SHEET].fetch(s, QUARTERLY)
        except errors:
            records = []
        points = sorted((pd.Timestamp(r.available_at), float(r.values[SHARES_OUTSTANDING])) for r in records
                        if r.available_at is not None and r.values.get(SHARES_OUTSTANDING) is not None)
        volume = panels["volume"][s].dropna() if s in panels["volume"] else pd.Series(dtype=float)
        if not points or volume.empty:
            continue
        shares = (np.array([p[0] for p in points], dtype="datetime64[ns]"), np.array([p[1] for p in points]))
        pos = volume.index.searchsorted(month_ends, side="right") - 1
        values = volume.to_numpy()
        for t, p in zip(month_ends, pos):
            if p < 0 or (t - volume.index[p]).days > FILL_SESSIONS + 4:
                continue
            count = window_as_of(shares, np.datetime64(t, "ns"), 1, False, policy)
            if count is None:
                continue
            row = {"date": t, "asset": s}
            for f in factors:
                row[f.name] = f.calculate({"volumes": values[max(0, p + 1 - f.PERIOD):p + 1].tolist(),
                                           "shares_outstanding": count})
            rows.append(row)
        if i % 100 == 0:
            log(f"  turnover: {i}/{len(symbols)} symbols ({time.time() - t0:.0f}s)")
    if not rows:
        return pd.DataFrame(columns=[f.name for f in factors],
                            index=pd.MultiIndex.from_arrays([[], []], names=["date", "asset"]))
    return pd.DataFrame(rows).set_index(["date", "asset"]).astype(float)


def fundamental_features(symbols: List[str], month_ends: pd.DatetimeIndex, log=print) -> pd.DataFrame:
    """The 75 point-in-time fundamental candidates at each month end (Eulerpool statements from the file cache)."""
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_fundamentals import (
        CSMFundamentals,
        available_candidates,
    )
    sources, errors = sp500_data.statement_sources()
    names = available_candidates()
    fundamentals = CSMFundamentals([sources], names, errors=errors, log=lambda m: None)
    cols, t0 = {}, time.time()
    for i, n in enumerate(names, 1):
        cols[n] = fundamentals.panel(n, symbols, month_ends).stack(future_stack=True)
        if i % 15 == 0:
            log(f"  fundamentals: {i}/{len(names)} candidates ({time.time() - t0:.0f}s)")
    out = pd.DataFrame(cols)
    out.index = out.index.set_names(["date", "asset"])
    return out


def run(cfg: SP500BacktestConfig, out_dir: Optional[Path] = None, log=None) -> Path:
    log = log or (lambda m: print(m, flush=True))
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out_dir = Path(out_dir or mcb.RESULTS_DIR / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    data, panels, membership, symbols = load(cfg, log)
    dates = data.month_ends[(data.month_ends >= pd.Timestamp(cfg.start)) & (data.month_ends <= pd.Timestamp(cfg.end))]
    labels = mcb.true_classes(data.forward_returns(), data.members_at, cfg.n_quantiles)
    coverage = sp500_data.coverage(membership, panels["close"].ffill(limit=FILL_SESSIONS), dates)
    groups = " + ".join(g for g, on in (("liquidity/volume", cfg.liquidity_volume), ("turnover", cfg.turnover),
                                         ("fundamentals", cfg.fundamentals)) if on)
    info = dict(mcb.MODEL_INFO["csm"], name=f"CSM LightGBM + Optuna TPE (binary, S&P 500, {groups})")
    manifest = {"stamp": out_dir.name, "started_at": datetime.now().isoformat(timespec="seconds"),
                "config": asdict(cfg), "universe_label": "S&P 500 PIT",
                "universe": "S&P 500 point-in-time members (Wikipedia current list + history of changes, rolled back "
                            "to 2007); member-months without Eulerpool bars are left out",
                "prices": "Eulerpool daily OHLCV, split-adjusted, not dividend-adjusted (price returns)",
                "coverage_by_year": coverage.groupby(coverage.index.year)["share"].mean().round(3).to_dict(),
                "decision_dates": [d.date().isoformat() for d in dates], "git_commit": mcb._git_commit(),
                "models": {}}
    mcb._write(out_dir / "manifest.json", manifest)
    t0 = time.time()
    try:
        log("bar features ...")
        feats = bar_features(panels, symbols, data.month_ends, cfg, log)
        if cfg.turnover:
            log("turnover features ...")
            feats = feats.join(turnover_features(panels, symbols, data.month_ends, log), how="left")
        if cfg.fundamentals:
            log("fundamental features ...")
            feats = feats.join(fundamental_features(symbols, data.month_ends, log), how="left")
        feats = feats.replace([np.inf, -np.inf], np.nan)
        log(f"features: {feats.shape[1]} candidates, {len(feats)} rows")
        pred = mcb.walk_forward(lambda: mcb.CSMClassifier(cfg.csm_trials), feats, labels, "true_2", dates,
                                data.members_at, _wf_config(cfg), log)
        obs = mcb.observations(pred, labels, info["classes"], "true_2")
        obs.to_csv(out_dir / "csm.csv", index=False)
        manifest["models"]["csm"] = {**{k: v for k, v in info.items() if k != "true"}, "file": "csm.csv",
                                     "observations": int(len(obs)), "runs": sorted(int(r) for r in obs["run_id"].unique()),
                                     "candidates": int(feats.shape[1]), "status": "completed",
                                     "seconds": round(time.time() - t0, 1)}
    except Exception as e:
        manifest["models"]["csm"] = {**{k: v for k, v in info.items() if k != "true"}, "status": "failed",
                                     "error": repr(e), "seconds": round(time.time() - t0, 1)}
        mcb._write(out_dir / "manifest.json", manifest)
        raise
    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    mcb._write(out_dir / "manifest.json", manifest)
    log(f"done: {manifest['models']['csm']['observations']} observations in {manifest['models']['csm']['seconds']}s")
    return out_dir


def _wf_config(cfg: SP500BacktestConfig) -> mcb.MonthlyBacktestConfig:
    return mcb.MonthlyBacktestConfig(start=cfg.start, end=cfg.end, training_window_months=cfg.training_window_months,
                                     min_training_months=cfg.min_training_months,
                                     retrain_every_months=cfg.retrain_every_months, n_quantiles=cfg.n_quantiles,
                                     csm_trials=cfg.csm_trials, models=("csm",))


def main(argv=None):
    p = argparse.ArgumentParser(description="Monthly walk-forward CSM backtest on the S&P 500")
    p.add_argument("--start", default=SP500BacktestConfig.start)
    p.add_argument("--end", default=SP500BacktestConfig.end)
    p.add_argument("--csm-trials", type=int, default=SP500BacktestConfig.csm_trials)
    p.add_argument("--no-fundamentals", action="store_true")
    p.add_argument("--no-turnover", action="store_true")
    a = p.parse_args(argv)
    print(run(SP500BacktestConfig(start=a.start, end=a.end, csm_trials=a.csm_trials,
                                  fundamentals=not a.no_fundamentals, turnover=not a.no_turnover)))


if __name__ == "__main__":
    main()
