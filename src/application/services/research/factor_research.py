"""
Factor research: a primary factor against comparison factors over a company-share universe, an interval and a
frequency.

Data (FactorResearchData, through the repositories):
* universe membership is POINT-IN-TIME: a (timestamp, security) value counts only while the security is a
  constituent (start_date <= day < end_date); nothing outside membership is used;
* timestamps are mapped to the bar they belong to (bar_key of the frequency); a factor stamped t uses data known
  at t, and its forward return starts at the close of that bar, so no value is paired with an earlier return;
* forward returns come from the stored raw TRADES closes of the same frequency; no close is filled.

Outputs keep three correlation notions apart: pooled (security-time pairs), cross-sectional (per timestamp, then
summarised) and time-series (between the long-short quantile portfolio returns of two factors).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.research import statistics as st
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key

ENTITY_TYPE = "CompanyShare"


def bar_minutes_of(frequency: str) -> Optional[int]:
    """None for daily (or longer) frequencies, minutes for intraday ones (Factor.FREQUENCIES keys)."""
    from src.domain.entities.factor.factor import Factor
    seconds = Factor.frequency_to_seconds(frequency) if hasattr(Factor, "frequency_to_seconds") else None
    if seconds is None:
        meta = Factor.FREQUENCIES.get(frequency)
        seconds = meta["seconds"] if meta else None
    if seconds is None:
        raise ValueError(f"unknown frequency '{frequency}'")
    return None if seconds >= 86400 else max(1, int(seconds // 60))


def periods_per_year(frequency: str) -> float:
    minutes = bar_minutes_of(frequency)
    from src.domain.entities.factor.factor import Factor
    seconds = Factor.FREQUENCIES[frequency]["seconds"]
    if minutes is None:
        return 252.0 * 86400 / seconds if seconds < 7 * 86400 else 365.25 * 86400 / seconds
    return 252.0 * 390.0 / minutes


@dataclass
class ResearchConfig:
    universe_id: int
    start: str
    end: str
    frequency: str
    primary_factor_id: int
    comparison_factor_ids: List[int] = field(default_factory=list)
    method: str = st.PEARSON
    n_quantiles: int = 5
    horizons: List[int] = field(default_factory=lambda: [1])
    min_obs: int = st.MIN_OBS
    min_assets: int = 5


class FactorResearchData:
    """Reads universes, factor definitions, PIT membership, factor panels and closes through the repositories."""

    def __init__(self, factory):
        self.factory = factory

    def universes(self) -> List[Dict]:
        repo = self.factory.investment_universe_local_repo
        out = []
        for u in repo.get_all() or []:
            members = self.factory.universe_constituent_local_repo.get_by_universe(u.id)
            out.append({"id": u.id, "name": u.name, "entity_type": getattr(u, "entity_type", None),
                        "constituents": len(members),
                        "active_now": sum(1 for m in members if m.end_date is None)})
        return out

    def membership(self, universe_id: int) -> List[tuple]:
        """[(entity_id, start_date, end_date or None)] of every membership period."""
        return [(int(m.entity_id), m.start_date, m.end_date)
                for m in self.factory.universe_constituent_local_repo.get_by_universe(universe_id)]

    def symbols(self, entity_ids: List[int]) -> Dict[int, str]:
        repo = self.factory.get_local_repository("CompanyShare")
        out = {}
        for eid in entity_ids:
            e = repo.get_by_id(eid) if repo is not None else None
            out[eid] = getattr(e, "symbol", None) or str(eid)
        return out

    def factors(self) -> List[Dict]:
        """Company-share factor definitions (id, name, group, subgroup, frequency, source, type)."""
        repo = self.factory.factor_local_repo
        out = []
        for f in repo.get_all() or []:
            ftype = getattr(f, "factor_type", None) or type(f).__name__
            if "company_share" not in str(ftype).lower() and "CompanyShare" not in type(f).__name__:
                continue
            out.append({"id": f.id, "name": f.name, "group": f.group, "subgroup": f.subgroup,
                        "frequency": getattr(f, "frequency", None), "source": getattr(f, "source", None),
                        "type": type(f).__name__})
        return sorted(out, key=lambda d: (d["group"] or "", d["name"] or ""))

    def factor(self, factor_id: int) -> Optional[Dict]:
        return next((f for f in self.factors() if f["id"] == factor_id), None)

    def panel(self, factor_id: int, entity_ids: List[int], start, end) -> pd.DataFrame:
        rows = self.factory.factor_value_local_repo.get_values_panel(
            [factor_id], entity_ids, ENTITY_TYPE, pd.Timestamp(start).to_pydatetime(), pd.Timestamp(end).to_pydatetime())
        if not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(rows, columns=["factor_id", "entity_id", "date", "value"])
        return frame.pivot_table(index="date", columns="entity_id", values="value", aggfunc="last").sort_index()

    def date_range(self, factor_ids: List[int], universe_id: Optional[int] = None) -> Dict[str, Optional[str]]:
        """First and last day with stored values of these factors (for the universe's shares when given)."""
        entity_ids = sorted({m[0] for m in self.membership(universe_id)}) if universe_id else None
        first, last = self.factory.factor_value_local_repo.get_date_range(factor_ids, entity_ids, ENTITY_TYPE)
        return {"first": first.strftime("%Y-%m-%d") if first else None,
                "last": last.strftime("%Y-%m-%d") if last else None}

    def close_factor_id(self, frequency: str) -> Optional[int]:
        """The raw TRADES close factor of the frequency (what forward returns are computed from)."""
        for f in self.factors():
            if f["name"] == "close" and f["frequency"] == frequency and f["source"] != "calculated" \
                    and f["subgroup"] == "TRADES":
                return f["id"]
        return None


def inclusive_end(value) -> pd.Timestamp:
    """An end given as a calendar date (no time) covers that whole day."""
    ts = pd.Timestamp(value)
    if isinstance(value, str) and len(value.strip()) <= 10:
        return ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return ts


def to_bars(panel: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Each timestamp mapped to its bar (the last value of a bar when several fall in it)."""
    if panel.empty:
        return panel
    minutes = bar_minutes_of(frequency)
    keys = pd.DatetimeIndex([bar_key(t, minutes) for t in panel.index])
    return panel.groupby(keys).last().sort_index()


def membership_mask(index: pd.DatetimeIndex, columns, membership: List[tuple]) -> pd.DataFrame:
    """True where the security is a constituent on that day (start <= day < end)."""
    mask = pd.DataFrame(False, index=index, columns=columns)
    days = index.normalize()
    for eid, start, end in membership:
        if eid not in mask.columns:
            continue
        ok = days >= pd.Timestamp(start)
        if end is not None:
            ok &= days < pd.Timestamp(end)
        mask[eid] = mask[eid] | ok
    return mask


@dataclass
class ResearchResult:
    config: ResearchConfig
    names: Dict[int, str]                              # factor id -> label
    primary_stats: Dict
    primary_profile: pd.DataFrame
    primary_values: np.ndarray
    matrix: pd.DataFrame
    matrix_counts: pd.DataFrame
    matrix_notes: Dict
    pooled: Dict[int, st.Correlation]
    cross_sectional: Dict[int, st.CrossSectionalCorrelations]
    quantiles: Optional[st.QuantilePortfolios]
    quantile_performance: Dict[str, Dict]
    long_short_correlations: Optional[pd.DataFrame]
    ic_by_horizon: Dict[int, Dict]
    securities: int
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def analyse_panels(cfg: ResearchConfig, panels: Dict[int, pd.DataFrame], names: Dict[int, str],
                   closes: Optional[pd.DataFrame], mask: pd.DataFrame) -> ResearchResult:
    """All research outputs from in-memory panels (bar-keyed, PIT-masked); testable without a database."""
    warnings, notes = [], []
    primary = panels.get(cfg.primary_factor_id, pd.DataFrame())
    if primary.empty:
        raise ValueError(f"no stored values of {names.get(cfg.primary_factor_id)} for this universe and interval")
    stats = st.describe_panel(primary, expected_cells=int(mask.reindex(index=primary.index,
                                                                         columns=primary.columns).fillna(False).to_numpy().sum()))
    profile = st.cross_sectional_profile(primary)
    ids = [cfg.primary_factor_id] + [f for f in cfg.comparison_factor_ids if f != cfg.primary_factor_id]
    stacked = {}
    for fid in ids:
        p = panels.get(fid)
        if p is None or p.empty:
            warnings.append(f"{names.get(fid, fid)}: no stored values in this universe and interval")
            continue
        stacked[names[fid]] = p.stack()
    frame = pd.DataFrame(stacked)
    coef, counts, mnotes = st.correlation_matrix(frame, cfg.method, cfg.min_obs)
    pooled, xs = {}, {}
    for fid in cfg.comparison_factor_ids:
        p = panels.get(fid)
        if fid == cfg.primary_factor_id or p is None or p.empty:
            continue
        pooled[fid] = st.pooled_correlation(primary, p, cfg.method, cfg.min_obs)
        xs[fid] = st.cross_sectional_correlations(primary, p, cfg.method, cfg.min_assets)
    q, qperf, ls_corr, ic = None, {}, None, {}
    ppy = periods_per_year(cfg.frequency)
    if closes is not None and not closes.empty:
        fwd1 = st.forward_returns(closes, 1).where(mask.reindex(index=closes.index, columns=closes.columns).fillna(False))
        q = st.quantile_portfolios(primary, fwd1, cfg.n_quantiles, cfg.min_assets)
        for col in q.returns.columns:
            qperf[col] = st.performance(q.returns[col], ppy)
        notes.append(f"Quantile portfolios: rebalanced every bar, equal weight, held one bar; Sharpe = mean / std x "
                     f"sqrt({ppy:g}) with no risk-free rate subtracted; no transaction costs.")
        notes.append("Value-weighted portfolios: unavailable (no market capitalisation is stored for these shares).")
        ls = {names[cfg.primary_factor_id]: q.returns.iloc[:, -1]}
        for fid in cfg.comparison_factor_ids:
            p = panels.get(fid)
            if fid != cfg.primary_factor_id and p is not None and not p.empty:
                ls[names[fid]] = st.quantile_portfolios(p, fwd1, cfg.n_quantiles, cfg.min_assets).returns.iloc[:, -1]
        if len(ls) > 1:
            ls_corr = st.correlation_matrix(pd.DataFrame(ls), cfg.method, cfg.min_obs)[0]
        for h in sorted(set(cfg.horizons)):
            fwd = st.forward_returns(closes, h).where(mask.reindex(index=closes.index, columns=closes.columns)
                                                       .fillna(False))
            x = st.cross_sectional_correlations(primary, fwd, st.SPEARMAN, cfg.min_assets)
            ic[h] = {**x.summary, "series": x.by_date}
        notes.append("Information coefficient: Spearman rank correlation, per timestamp, between the factor and the "
                     "forward return from the close of its bar to the close h bars later (overlapping when h > 1).")
    else:
        warnings.append(f"no stored TRADES close at frequency {cfg.frequency}: portfolio and forward-return analyses "
                        f"are unavailable")
    return ResearchResult(config=cfg, names=names, primary_stats=stats, primary_profile=profile,
                          primary_values=primary.to_numpy(dtype=float).ravel(), matrix=coef, matrix_counts=counts,
                          matrix_notes=mnotes, pooled=pooled, cross_sectional=xs, quantiles=q,
                          quantile_performance=qperf, long_short_correlations=ls_corr, ic_by_horizon=ic,
                          securities=int(primary.notna().any(axis=0).sum()), notes=notes, warnings=warnings)


class FactorResearchService:

    def __init__(self, data: FactorResearchData):
        self.data = data

    def run(self, cfg: ResearchConfig) -> ResearchResult:
        start, end = pd.Timestamp(cfg.start), inclusive_end(cfg.end)
        if end <= start:
            raise ValueError("the end must be after the start")
        if cfg.method not in st.METHODS:
            raise ValueError(f"unknown correlation method '{cfg.method}'")
        membership = self.data.membership(cfg.universe_id)
        if not membership:
            raise ValueError("the universe has no constituents")
        entity_ids = sorted({m[0] for m in membership})
        defs = {f["id"]: f for f in self.data.factors()}
        ids = [cfg.primary_factor_id] + list(cfg.comparison_factor_ids)
        unknown = [i for i in ids if i not in defs]
        if unknown:
            raise ValueError(f"unknown factor id(s) {unknown}")
        notes = []
        mismatched = [defs[i]["name"] for i in ids if defs[i]["frequency"] != cfg.frequency]
        if mismatched:
            notes.append(f"factors stored at another frequency than {cfg.frequency}: {mismatched} — mapped to "
                         f"{cfg.frequency} bars as stored (no resampling of their values)")
        names = {i: f"{defs[i]['name']} [{defs[i]['frequency']}, #{i}]" for i in ids}
        panels = {}
        for fid in ids:
            p = to_bars(self.data.panel(fid, entity_ids, start, end), cfg.frequency)
            if not p.empty:
                m = membership_mask(p.index, p.columns, membership)
                p = p.where(m)
            panels[fid] = p
        index = pd.DatetimeIndex(sorted(set().union(*[set(p.index) for p in panels.values() if not p.empty])))
        close_id = self.data.close_factor_id(cfg.frequency)
        closes = None
        if close_id is not None:
            closes = to_bars(self.data.panel(close_id, entity_ids, start, end + pd.Timedelta(days=10)), cfg.frequency)
        result = analyse_panels(cfg, panels, names, closes, membership_mask(
            closes.index if closes is not None and not closes.empty else index, entity_ids, membership))
        result.notes = notes + result.notes + [
            "Universe membership is point-in-time: values are used only while the security is a constituent.",
            "Pairwise deletion: every statistic uses only the observations present in all its inputs; the counts are "
            "shown."]
        return result
