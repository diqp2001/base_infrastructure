"""
src/domain/entities/factor/finance/financial_assets/share_factor/etf_share/etf_share_realized_dispersion_factor.py

Realized ATM option dispersion of an ETF share over a holding period of `months` (21 trading days per month):

    call payoff   C = max(S_T / S_t - 1, 0)          put payoff   P = max(1 - S_T / S_t, 0)
    D_call = sum_i w_i C_i - C_ETF                    D_put  = sum_i w_i P_i - P_ETF

the options struck at the close of t (21 x months bars before the value's date) and settled at the close of T (the
value's date). Known at T, so the value is stored at T (no look-ahead, like return_21d). Note: C - P = r for every
instrument, so D_call - D_put = sum_i w_i r_i - r_ETF (the tracking difference).

Name: realized_<call|put>_<dispersion|etf|basket|weight_coverage|constituents|etf_return>_<1..6>m.
Resolution branch A - calculate() receives (DependencySpec.endpoints: the full window must exist, only its first and
last closes are passed and recorded in the lineage):
    'etf_close'         the ETF's [start close, end close]                       (ETFShareFactor close)
    'constituent_close' {constituent symbol: [start close, end close]}           (CompanyShareFactor close, per entity)
    'weights'           {constituent symbol: weight} in force at the start        (injected by the resolution service)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_dispersion_factor import (
    BARS_PER_MONTH, CALL, ETFShareDispersionFactor, months_before, normalize_weights,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor


def option_payoff(right: str, start: float, end: float) -> float:
    """An ATM option's payoff per unit of its strike (= the start price)."""
    r = end / start - 1.0
    return max(r, 0.0) if right == CALL else max(-r, 0.0)


class ETFShareRealizedDispersionFactor(ETFShareDispersionFactor):
    """Realized ATM call / put dispersion of an ETF share (see the module docstring)."""

    KIND = "realized"
    MEASURES = ("dispersion", "etf", "basket", "weight_coverage", "constituents", "etf_return")

    def __init__(self, name: str = "realized_call_dispersion_1m", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def lookback(self) -> Optional[int]:
        """Closes in the window: the start bar plus 21 per month."""
        return BARS_PER_MONTH * self.months + 1 if self.months else None

    def related_as_of(self, target_date):
        """The start of the holding period: its constituents and weights are the observation's."""
        day = target_date.date() if isinstance(target_date, datetime) else target_date
        return months_before(day, self.months) if self.months else day

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
            CompanyShareFactor,
        )
        if not self.months:
            return []
        return [
            DependencySpec(factor_type=ETFShareFactor, group="price", name_in=["close"], frequency="1d",
                           lookback=self.lookback, endpoints=True, key="etf_close"),
            DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=["close"], frequency="1d",
                           lookback=self.lookback, endpoints=True, key="constituent_close", per_entity=True),
        ]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        etf = dependencies.get("etf_close") or []
        closes = dependencies.get("constituent_close") or {}
        weights = dependencies.get("weights") or {}
        if not self.months or not weights:
            return None
        legs = {s: (float(v[0]), float(v[-1])) for s, v in closes.items()
                if v and len(v) >= 2 and float(v[0]) > 0 and float(v[-1]) > 0}
        w, coverage = normalize_weights(weights, legs)
        if len(etf) < 2 or float(etf[0]) <= 0 or float(etf[-1]) <= 0 or not w:
            return self._select(None, coverage)
        start, end = float(etf[0]), float(etf[-1])
        etf_payoff = option_payoff(self.right, start, end)
        basket = sum(wi * option_payoff(self.right, *legs[s]) for s, wi in w.items())
        return self._select({"dispersion": basket - etf_payoff, "etf": etf_payoff, "basket": basket,
                             "constituents": float(len(w)), "etf_return": end / start - 1.0}, coverage)
