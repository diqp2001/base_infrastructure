"""
Factors computed from a window of raw stored prices, resolved by FactorValueResolutionService through
DependencySpec(..., lookback=N) (see FactorValueRepository.get_closed_bar_series: closed bars only).

SeriesPriceReturn — the price return of the instrument over the window its definition names:

    subgroup 'daily'   -> 2 closes  (last closed close vs the one before)
    subgroup 'weekly'  -> 6 closes  (5 trading days)
    subgroup 'monthly' -> 22 closes (21 trading days)
    subgroup 'minutes' -> 2 opens   (consecutive bars)

A subclass names the raw factor type of its instrument (RAW_FACTOR_TYPE). `calculate(dependencies)` is the
resolution-service path; any other call goes to `price_return(...)`, the explicit two-price form.
"""

from typing import Optional

from src.domain.entities.factor.dependency_spec import DependencySpec

RETURN_WINDOWS = {"daily": ("close", 2), "weekly": ("close", 6), "monthly": ("close", 22), "minutes": ("open", 2)}


def mean_or_none(values):
    values = [float(v) for v in (values or []) if v is not None]
    return sum(values) / len(values) if values else None


class SeriesPriceReturn:

    RAW_FACTOR_TYPE = None          # set by the subclass: the instrument's raw (stored) price factor

    def raw_factor_type(self):
        return self.RAW_FACTOR_TYPE

    def return_window(self):
        """(raw field, number of bars) for the definition's subgroup; daily when the subgroup is not a window."""
        return RETURN_WINDOWS.get(getattr(self, "subgroup", None) or "daily", RETURN_WINDOWS["daily"])

    @property
    def calculate_dependencies(self) -> list:
        field, bars = self.return_window()
        return [DependencySpec(factor_type=self.raw_factor_type(), group="price", name_in=[field],
                               source_not_in=["calculated"], lookback=bars, key="prices")]

    def calculate(self, dependencies=None, *args, **kwargs) -> Optional[float]:
        if isinstance(dependencies, dict):
            prices = [float(p) for p in (dependencies.get("prices") or []) if p is not None]
            if len(prices) < 2 or prices[0] <= 0 or prices[-1] <= 0:
                return None
            return prices[-1] / prices[0] - 1
        if dependencies is not None:
            args = (dependencies,) + args
        return self.price_return(*args, **kwargs)
