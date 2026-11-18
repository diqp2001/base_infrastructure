"""
Point-in-time FUNDAMENTAL candidates of the cross-sectional classifier (opt-in: CSMFeatureConfig.fundamentals).

A fundamental candidate is a calculated fundamental factor of the domain (CompanyShareFundamental{Profitability,
Leverage,Growth}Factor) on quarterly ('1q') or annual ('1y') statements, named

    fund_<factor name>_<frequency>        e.g. fund_roe_ttm_1q, fund_net_income_growth_yoy_1q, fund_roa_1y

and computed by ITS OWN calculate() on the statement windows its DependencySpecs ask for, read exactly as
FactorValueResolutionService reads a point-in-time series (Factor.point_in_time_policy):

    every canonical field of a statement is a series stamped at the record's publication (StatementRecord.available_at);
    at time t the window = the ``lookback`` (else 1) latest values stamped <= t, none when fewer are known, when the
    newest is older than max_age or when two neighbours are more than max_gap apart; ``endpoints`` keeps the first
    and the last. Several providers: ONE per input, the first whose window is complete (STATEMENT_SOURCES order).

So a value at a bar never uses a statement published after that bar. Statements come from
FinancialStatementSourcePort (any provider: FMP, Eulerpool, ...), fetched once per (symbol, statement, frequency)
and kept in memory: nothing is written to the database.

Not candidates: the valuation factors (they read a daily close; the classifier's bars may be intraday) and the
statement item totals (levels in currency: not comparable across companies).
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Type

import numpy as np
import pandas as pd

from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    ANNUAL, QUARTERLY, CompanyShareFundamentalFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_growth_factor import (
    CompanyShareFundamentalGrowthFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_leverage_factor import (
    CompanyShareFundamentalLeverageFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import (
    CompanyShareFundamentalProfitabilityFactor,
)
from src.domain.ports.factor.financial_statement_source_port import FinancialStatementSourcePort, StatementRecord

logger = logging.getLogger(__name__)

PREFIX = "fund_"
FREQUENCIES = (QUARTERLY, ANNUAL)
FUNDAMENTAL_FACTOR_CLASSES: Tuple[Type[CompanyShareFundamentalFactor], ...] = (
    CompanyShareFundamentalProfitabilityFactor,
    CompanyShareFundamentalLeverageFactor,
    CompanyShareFundamentalGrowthFactor,
)

# a statement provider = {statement: FinancialStatementSourcePort}
StatementSources = Mapping[str, FinancialStatementSourcePort]
Series = Tuple[np.ndarray, np.ndarray]          # (stamps as datetime64[ns], values), stamps ascending


def is_fundamental(name: str) -> bool:
    return str(name).startswith(PREFIX)


def feature_name(factor_name: str, frequency: str) -> str:
    return f"{PREFIX}{factor_name}_{frequency}"


def fundamental_factor(name: str) -> CompanyShareFundamentalFactor:
    """The domain factor of a candidate name; ValueError when the name is not a usable fundamental candidate."""
    if not is_fundamental(name):
        raise ValueError(f"{name!r} is not a fundamental candidate (prefix {PREFIX!r})")
    body = name[len(PREFIX):]
    factor_name, _, frequency = body.rpartition("_")
    if frequency not in FREQUENCIES:
        raise ValueError(f"{name!r}: frequency suffix must be one of {FREQUENCIES}")
    for cls in FUNDAMENTAL_FACTOR_CLASSES:
        if cls.parse_name(factor_name)[0] is not None:
            factor = cls(name=factor_name, frequency=frequency)
            if not factor.usable:
                raise ValueError(f"{name!r}: {cls.__name__} {factor_name!r} is not defined at frequency {frequency}")
            return factor
    raise ValueError(f"{name!r}: {factor_name!r} is not a measure of {[c.__name__ for c in FUNDAMENTAL_FACTOR_CLASSES]}")


def available_candidates() -> List[str]:
    """Every usable fundamental candidate name."""
    out = []
    for cls in FUNDAMENTAL_FACTOR_CLASSES:
        for frequency in FREQUENCIES:
            for ttm in (False, True):
                for factor_name in cls.factor_names(ttm=ttm):
                    factor = cls(name=factor_name, frequency=frequency)
                    if factor.usable:
                        out.append(feature_name(factor_name, frequency))
    return out


def _policy(frequency: str) -> Dict[str, float]:
    return Factor.POINT_IN_TIME_POLICY[frequency]


def window_as_of(series: Series, t: np.datetime64, count: int, endpoints: bool, policy: Dict[str, float]
                 ) -> Optional[List[float]]:
    """The window of a point-in-time series known at ``t`` (the resolver's _values_as_of rule), or None."""
    stamps, values = series
    k = int(np.searchsorted(stamps, t, side="right"))
    if k < count:
        return None
    s = stamps[k - count:k]
    if (t - s[-1]) / np.timedelta64(1, "s") > policy["max_age"]:
        return None
    if count > 1 and (np.diff(s) / np.timedelta64(1, "s") > policy["max_gap"]).any():
        return None
    w = values[k - count:k].tolist()
    return [w[0], w[-1]] if endpoints and len(w) > 2 else w


class CSMFundamentals:
    """Point-in-time values of the fundamental candidates, per asset, from one or more statement providers (in
    preference order). ``errors`` = the providers' request errors: logged, the asset has no value."""

    def __init__(self, providers: Sequence[StatementSources], names: Sequence[str],
                 errors: Tuple[Type[BaseException], ...] = (), log: Optional[Callable[[str], None]] = None):
        self.providers = [dict(p) for p in providers]
        self.factors = {n: fundamental_factor(n) for n in names}
        self.errors = tuple(errors)
        self.log = log or logger.info
        self._series: Dict[Tuple[int, str, str, str], Dict[str, Series]] = {}   # (provider, symbol, stmt, freq)
        self._events: Dict[Tuple[str, str], pd.Series] = {}

    @property
    def names(self) -> List[str]:
        return list(self.factors)

    # -- statements --
    def _records(self, p: int, symbol: str, statement: str, frequency: str) -> Dict[str, Series]:
        """{field: (stamps, values)} of one provider's statement for a symbol (fetched once)."""
        key = (p, symbol, statement, frequency)
        if key in self._series:
            return self._series[key]
        source = self.providers[p].get(statement)
        out: Dict[str, Series] = {}
        if source is not None and frequency in getattr(source, "FREQUENCIES", ()):
            try:
                records: List[StatementRecord] = source.fetch(symbol, frequency)
            except self.errors as e:
                self.log(f"[CSM] fundamentals {statement} {frequency} {symbol}: {e}")
                records = []
            points: Dict[str, Dict[pd.Timestamp, float]] = {}
            for r in records:
                stamp = r.available_at
                if stamp is None:
                    continue
                for name, v in r.values.items():
                    if v is not None and np.isfinite(float(v)):
                        points.setdefault(name, {})[pd.Timestamp(stamp)] = float(v)
            for name, by_stamp in points.items():
                stamps = sorted(by_stamp)
                out[name] = (np.array(stamps, dtype="datetime64[ns]"), np.array([by_stamp[s] for s in stamps]))
        self._series[key] = out
        return out

    def _inputs(self, factor: CompanyShareFundamentalFactor):
        """[(key, statement, frequency, field, count, endpoints)] of the factor's statement dependencies."""
        out = []
        for spec in factor.calculate_dependencies:
            lookback = getattr(spec, "lookback", None)
            out.append((spec.result_key, spec.subgroup, factor.frequency, list(spec.name_in)[0],
                        int(lookback) if lookback else 1, bool(getattr(spec, "endpoints", False))))
        return out

    # -- values --
    def events(self, symbol: str, name: str) -> pd.Series:
        """The candidate's value from each moment it can change (a publication, or a window expiring), ascending;
        NaN = no value from then on."""
        key = (symbol, name)
        if key in self._events:
            return self._events[key]
        factor = self.factors[name]
        inputs = self._inputs(factor)
        policy = _policy(factor.frequency)
        series = {}
        moments = set()
        for dep_key, statement, frequency, field, _, _ in inputs:
            for p in range(len(self.providers)):
                s = self._records(p, symbol, statement, frequency).get(field)
                if s is None:
                    continue
                series[(dep_key, p)] = s
                moments.update(s[0].tolist())
                expiry = s[0] + np.timedelta64(int(policy["max_age"]), "s") + np.timedelta64(1, "s")
                moments.update(expiry.tolist())
        values = {}
        for m in sorted(moments):
            t = np.datetime64(m, "ns")
            dependencies = {}
            for dep_key, _, _, _, count, endpoints in inputs:
                for p in range(len(self.providers)):
                    s = series.get((dep_key, p))
                    w = window_as_of(s, t, count, endpoints, policy) if s is not None else None
                    if w is not None:
                        dependencies[dep_key] = w
                        break
            try:
                v = factor.calculate(dependencies) if len(dependencies) == len(inputs) else None
            except (ValueError, ZeroDivisionError, TypeError):
                v = None
            values[pd.Timestamp(t)] = float(v) if v is not None and np.isfinite(float(v)) else np.nan
        out = pd.Series(values, dtype=float).sort_index()
        self._events[key] = out
        return out

    def series(self, symbol: str, name: str, index: pd.DatetimeIndex) -> pd.Series:
        """The candidate's value at every date of ``index`` (the latest event at or before it)."""
        ev = self.events(symbol, name)
        if ev.empty:
            return pd.Series(np.nan, index=index)
        pos = np.searchsorted(ev.index.values, pd.DatetimeIndex(index).values, side="right") - 1
        vals = np.where(pos >= 0, ev.to_numpy()[np.clip(pos, 0, None)], np.nan)
        return pd.Series(vals, index=index)

    def panel(self, name: str, symbols: Sequence[str], index: pd.DatetimeIndex) -> pd.DataFrame:
        return pd.DataFrame({s: self.series(s, name, index) for s in symbols}, index=index)

    def coverage(self, symbols: Sequence[str], when) -> pd.DataFrame:
        """{candidate: share of symbols with a value at ``when``} (rows) - a data check, not used by the model."""
        t = pd.DatetimeIndex([pd.Timestamp(when)])
        rows = {n: float(np.mean([np.isfinite(self.series(s, n, t).iloc[0]) for s in symbols])) for n in self.factors}
        return pd.Series(rows, name="coverage").sort_values(ascending=False).to_frame()


def statement_sources_of(provider) -> StatementSources:
    """{statement: FinancialStatementSourcePort} of a statement factor value repository (its ``statements``)."""
    statements = getattr(provider, "statements", None)
    if not statements:
        raise ValueError(f"{type(provider).__name__} has no financial statements")
    return statements
