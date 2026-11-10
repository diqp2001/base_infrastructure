"""
src/domain/entities/factor/finance/financial_assets/share_factor/etf_share/etf_share_dispersion_factor.py

Shared mechanics of the ETF option dispersion factors - not a factor of its own (no stored series, no ORM identity):
the two dispersion factors are separate classes with their own formula and dependencies,
    ETFShareRealizedDispersionFactor   realized payoffs from the closes        (etf_share_realized_dispersion_factor.py)
    ETFShareImpliedDispersionFactor    option premiums from the ATM series     (etf_share_implied_dispersion_factor.py)

Dispersion = sum_i w_i x_i - x_ETF, each x per unit of its own instrument's price. The factor's name carries its
parameters, like the return factors' horizons:

    <kind>_<right>_<measure>_<months>m        e.g. realized_call_dispersion_3m, implied_put_basket_1m

    right    call | put
    measure  dispersion      basket - ETF (the factor proper)
             etf             the ETF option's normalized payoff / premium
             basket          sum_i w_i x the constituents' normalized payoffs / premiums
             weight_coverage share of the ETF's weight with data
             constituents    number of constituents with data
             etf_return      (realized only) the ETF's return over the holding period
    months   1 .. 6

Weights: the ETF's constituents and weights in force at the observation's start (the ETF share repository's related
entities / weights, injected as dependencies['weights']), renormalized over the constituents with data; below
MIN_WEIGHT_COVERAGE there is no value (a missing input is never a zero) - weight_coverage is still produced.
A stored row whose name is not of that form decodes with no parameters, no dependencies and no value.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Dict, Mapping, Optional, Tuple

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor

CALL, PUT = "call", "put"
RIGHTS = (CALL, PUT)
MONTHS = (1, 2, 3, 4, 5, 6)
BARS_PER_MONTH = 21
MIN_WEIGHT_COVERAGE = 1.0          # the owner's rule (2026-11-06): every constituent of the ETF has its data
NAME = re.compile(r"^(?P<kind>[a-z]+)_(?P<right>call|put)_(?P<measure>[a-z_]+?)_(?P<months>\d+)m$")


def dispersion_factor_name(kind: str, right: str, measure: str, months: int) -> str:
    return f"{kind}_{right}_{measure}_{months}m"


def months_before(d: date, months: int) -> date:
    """The same day `months` calendar months earlier (the month's last day when it has no such day)."""
    year, month = divmod(d.year * 12 + d.month - 1 - months, 12)
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month + 1, day)
        except ValueError:
            continue
    raise ValueError(d)


def normalize_weights(weights: Mapping[str, float], available) -> Tuple[Dict[str, float], float]:
    """The weights of the available constituents rescaled to sum to 1, and the share of the total weight they carry
    (weight coverage). Non-positive weights are ignored."""
    positive = {s: float(w) for s, w in weights.items() if w is not None and float(w) > 0.0}
    total = sum(positive.values())
    kept = {s: w for s, w in positive.items() if s in available}
    covered = sum(kept.values())
    if total <= 0.0 or covered <= 0.0:
        return {}, 0.0
    return {s: w / covered for s, w in kept.items()}, covered / total


class ETFShareDispersionFactor(ETFShareFactor):
    """Base of the ETF dispersion factors (see the module docstring). Subclasses set KIND / MEASURES and implement
    calculate_dependencies and calculate()."""

    KIND: str = ""
    MEASURES: Tuple[str, ...] = ()

    def __init__(self, name: str, group: str = "dispersion", subgroup: Optional[str] = None,
                 frequency: Optional[str] = "1d", data_type: Optional[str] = "numeric",
                 source: Optional[str] = "calculated", definition: Optional[str] = None,
                 factor_id: Optional[int] = None, **kwargs):
        params = self.parse_name(name) or {"right": None, "measure": None, "months": None}
        super().__init__(
            name=name, group=group, subgroup=subgroup or self.KIND, frequency=frequency, data_type=data_type,
            source=source, factor_id=factor_id,
            definition=definition or (f"ETF {self.KIND} ATM {params['right']} {params['measure']} over "
                                      f"{params['months']} month(s)" if params["months"] else name),
        )
        self.right, self.measure, self.months = params["right"], params["measure"], params["months"]

    @classmethod
    def parse_name(cls, name: str) -> Optional[Dict[str, object]]:
        m = NAME.match(name or "")
        if not m or m["kind"] != cls.KIND or m["measure"] not in cls.MEASURES or int(m["months"]) not in MONTHS:
            return None
        return {"right": m["right"], "measure": m["measure"], "months": int(m["months"])}

    def related_as_of(self, target_date):
        """The date whose constituents and weights the observation uses (default: the value's own date)."""
        return target_date.date() if isinstance(target_date, datetime) else target_date

    def _select(self, values: Optional[Dict[str, float]], coverage: float) -> Optional[float]:
        """The factor's measure from the computed values; None below the coverage threshold."""
        if self.measure == "weight_coverage":
            return coverage
        if values is None or coverage + 1e-12 < MIN_WEIGHT_COVERAGE:
            return None
        return values.get(self.measure)
