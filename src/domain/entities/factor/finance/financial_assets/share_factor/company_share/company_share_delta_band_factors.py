"""
CompanyShare delta-hedging no-trade bands of a reference call option, and the relative price moves that trigger
a rebalancing.

Reference option (one per share and session): a European CALL on the share
    S  = last close                       (TRADES close)
    K  = 4-month moving average of the close (84 sessions, 4 x 21)
    sigma = IBKR implied volatility of the share (close of the OPTION_IMPLIED_VOLATILITY series, annualised)
    r  = 13-week T-bill yield, IBKR index IRX (quoted as yield x 10: 45.05 -> 4.505%), continuously compounded
    tau = ``time_to_expiry_days`` / 365   (library parameter; 30 days = the horizon of IBKR's implied volatility)
Black-Scholes delta and gamma:  d1 = (ln(S/K) + (r + sigma^2/2) tau) / (sigma sqrt(tau)),  delta = N(d1),
gamma = n(d1) / (S sigma sqrt(tau)).

No-trade half-width H (delta units), proportional cost ``cost_rate`` k and CARA risk aversion ``risk_aversion`` a
(library parameters) — the two models of the SPX v2 hedging module:
    Whalley & Wilmott (1997):  H = [ (3/2) (k S / a) exp(r tau) |gamma| ]^(1/3)
    Zakamouline (2009):        H = sqrt( k S exp(r tau) |gamma| / (a sigma^2) )

Factors (per method): ceiling = delta + H, floor = delta - H (band values, delta units), and the relative distance to
each trigger: the relative stock-price move after which the call's delta reaches the ceiling (price up) or the floor
(price down), the other inputs unchanged —
    ceiling distance = S_up / S - 1,   floor distance = 1 - S_down / S,   S* = K exp(N^-1(target) sigma sqrt(tau)
                                                                                     - (r + sigma^2/2) tau)
A band edge outside (0, 1) cannot be reached by a call delta; the target is then taken at 1e-6 from the bound
(a large finite distance).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)

MA_WINDOW = 84                         # 4 months of sessions (4 x 21)
IRX_SYMBOL = "IRX"
IRX_QUOTE_SCALE = 1000.0               # IRX quotes the yield x 10, in percent: 45.05 -> 0.04505
DELTA_EPSILON = 1e-6
_N = NormalDist()


@dataclass
class DeltaBand:
    spot: float
    strike: float
    sigma: float
    rate: float
    tau: float
    delta: float
    gamma: float
    half_width: float

    @property
    def ceiling(self) -> float:
        return self.delta + self.half_width

    @property
    def floor(self) -> float:
        return self.delta - self.half_width

    def spot_at_delta(self, target: float) -> float:
        """Spot at which the call's delta equals ``target`` (other inputs unchanged)."""
        target = min(max(target, DELTA_EPSILON), 1.0 - DELTA_EPSILON)
        sqrt_tau = math.sqrt(self.tau)
        log_moneyness = _N.inv_cdf(target) * self.sigma * sqrt_tau - (self.rate + 0.5 * self.sigma ** 2) * self.tau
        return self.strike * math.exp(log_moneyness)

    @property
    def ceiling_distance(self) -> float:
        return self.spot_at_delta(self.ceiling) / self.spot - 1.0

    @property
    def floor_distance(self) -> float:
        return 1.0 - self.spot_at_delta(self.floor) / self.spot


def black_scholes_call_delta_gamma(spot: float, strike: float, sigma: float, rate: float, tau: float):
    sqrt_tau = math.sqrt(tau)
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma ** 2) * tau) / (sigma * sqrt_tau)
    return _N.cdf(d1), _N.pdf(d1) / (spot * sigma * sqrt_tau)


def whalley_wilmott_half_width(gamma: float, spot: float, cost_rate: float, risk_aversion: float,
                               rate: float, tau: float) -> float:
    return ((3.0 / 2.0) * (cost_rate * spot / risk_aversion) * math.exp(rate * tau) * abs(gamma)) ** (1.0 / 3.0)


def zakamouline_half_width(gamma: float, spot: float, cost_rate: float, risk_aversion: float,
                           rate: float, tau: float, sigma: float) -> float:
    return math.sqrt(cost_rate * spot * math.exp(rate * tau) * abs(gamma) / (risk_aversion * sigma ** 2))


def _values(dependencies: dict, key: str) -> List[float]:
    raw = dependencies.get(key) or []
    raw = raw if isinstance(raw, list) else [raw]
    return [float(v) for v in raw if v is not None]


def delta_band(dependencies: Dict, method: str) -> Optional[DeltaBand]:
    """The reference call's delta band from the resolved dependencies and the library parameters; None when any
    input is missing or invalid (no default value is ever substituted)."""
    params = dependencies.get("parameters") or {}
    try:
        cost_rate = float(params["cost_rate"])
        risk_aversion = float(params["risk_aversion"])
        tau = float(params["time_to_expiry_days"]) / 365.0
    except (KeyError, TypeError, ValueError):
        return None
    closes = _values(dependencies, "closes")
    vols = _values(dependencies, "implied_vols")
    rates = _values(dependencies, "rates")
    if len(closes) < MA_WINDOW or not vols or not rates:
        return None
    spot, strike, sigma = closes[-1], sum(closes[-MA_WINDOW:]) / MA_WINDOW, vols[-1]
    rate = math.log1p(rates[-1] / IRX_QUOTE_SCALE)
    if spot <= 0 or strike <= 0 or sigma <= 0 or tau <= 0 or cost_rate <= 0 or risk_aversion <= 0:
        return None
    delta, gamma = black_scholes_call_delta_gamma(spot, strike, sigma, rate, tau)
    if method == "whalley_wilmott":
        h = whalley_wilmott_half_width(gamma, spot, cost_rate, risk_aversion, rate, tau)
    elif method == "zakamouline":
        h = zakamouline_half_width(gamma, spot, cost_rate, risk_aversion, rate, tau, sigma)
    else:
        raise ValueError(f"unknown band method {method!r}")
    return DeltaBand(spot, strike, sigma, rate, tau, delta, gamma, h)


def delta_band_dependency_specs() -> list:
    from src.domain.entities.factor.dependency_spec import DependencySpec
    from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
    return [
        DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=["close"], source_not_in=["calculated"],
                       lookback=MA_WINDOW, key="closes"),
        DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=["close"], source_not_in=["calculated"],
                       subgroup="OPTION_IMPLIED_VOLATILITY", lookback=1, key="implied_vols"),
        DependencySpec(factor_type=IndexFactor, group="price", name_in=["close"], source_not_in=["calculated"],
                       lookback=1, key="rates", entity_symbol=IRX_SYMBOL, entity_type="Index"),
    ]


class _DeltaBandFactor(CompanyShareFactor):
    """One output of the reference call's band: METHOD x OUTPUT."""
    LIBRARY_PARAMETERS = True            # cost_rate, risk_aversion, time_to_expiry_days from the library entry
    METHOD = ""
    OUTPUT = ""                          # 'ceiling' | 'floor' | 'ceiling_distance' | 'floor_distance'
    DEFAULT_NAME = ""

    def __init__(self, factor_id: Optional[int] = None, name: Optional[str] = None, group: Optional[str] = "greek",
                 subgroup: Optional[str] = "delta", frequency: Optional[str] = "1d",
                 data_type: Optional[str] = "numeric", source: Optional[str] = "calculated",
                 definition: Optional[str] = None, **kwargs):
        super().__init__(name=name or self.DEFAULT_NAME, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, factor_id=factor_id,
                         definition=definition or f"{self.METHOD} delta-hedging band {self.OUTPUT} of the reference "
                                                  f"call (strike = 4-month moving average, IBKR implied vol)",
                         **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        return delta_band_dependency_specs()

    def calculate(self, dependencies: Dict) -> Optional[float]:
        band = delta_band(dependencies, self.METHOD)
        if band is None:
            return None
        value = getattr(band, self.OUTPUT)
        return float(value) if math.isfinite(value) else None


class CompanyShareZakamoulineDeltaCeilingFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "zakamouline", "ceiling", "zakamouline_delta_ceiling"


class CompanyShareZakamoulineDeltaFloorFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "zakamouline", "floor", "zakamouline_delta_floor"


class CompanyShareWhalleyWilmottDeltaCeilingFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "whalley_wilmott", "ceiling", "whalley_wilmott_delta_ceiling"


class CompanyShareWhalleyWilmottDeltaFloorFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "whalley_wilmott", "floor", "whalley_wilmott_delta_floor"


class CompanyShareZakamoulineCeilingDistanceFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "zakamouline", "ceiling_distance", "zakamouline_ceiling_distance"


class CompanyShareZakamoulineFloorDistanceFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "zakamouline", "floor_distance", "zakamouline_floor_distance"


class CompanyShareWhalleyWilmottCeilingDistanceFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "whalley_wilmott", "ceiling_distance", "whalley_wilmott_ceiling_distance"


class CompanyShareWhalleyWilmottFloorDistanceFactor(_DeltaBandFactor):
    METHOD, OUTPUT, DEFAULT_NAME = "whalley_wilmott", "floor_distance", "whalley_wilmott_floor_distance"


DELTA_BAND_FACTOR_CLASSES = (
    CompanyShareZakamoulineDeltaCeilingFactor, CompanyShareZakamoulineDeltaFloorFactor,
    CompanyShareWhalleyWilmottDeltaCeilingFactor, CompanyShareWhalleyWilmottDeltaFloorFactor,
    CompanyShareZakamoulineCeilingDistanceFactor, CompanyShareZakamoulineFloorDistanceFactor,
    CompanyShareWhalleyWilmottCeilingDistanceFactor, CompanyShareWhalleyWilmottFloorDistanceFactor,
)
