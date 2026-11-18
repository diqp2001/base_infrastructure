"""
Model price of a listed option on a share (company share or ETF share) when the market has no quote for it - e.g. any
expired contract in a backtest (IBKR keeps no history of expired options).

European Black-Scholes-Merton call / put, every input a factor value resolved by FactorValueResolutionService:
    S      = the underlying's last closed close (the price series' reading order: MIDPOINT, then TRADES)                         (dependency key 'spot')
    sigma  = the underlying's IBKR implied volatility: last close of its OPTION_IMPLIED_VOLATILITY series (30-day ATM
             implied vol, annualised)                                          (key 'implied_vol')
    r      = 13-week T-bill yield, IBKR index IRX (quoted as yield x 10: 45.05 -> 4.505 %), continuously compounded
                                                                               (key 'rate')
    q      = 0
    K, T, call / put = the option the value is resolved for (strike, calendar days to its expiry / 365)
On or after the expiry: the intrinsic value at the spot. Any input missing -> no value (no default is substituted).
The same inputs as the delta-band factors (company_share_delta_band_factors).
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_delta_band_factors import (
    IRX_QUOTE_SCALE,
    IRX_SYMBOL,
)

SPOT, IMPLIED_VOL, RATE = "spot", "implied_vol", "rate"


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _last(dependencies: dict, key: str) -> Optional[float]:
    raw = dependencies.get(key)
    if raw is None:
        return None
    values: List[float] = [float(v) for v in (raw if isinstance(raw, list) else [raw]) if v is not None]
    return values[-1] if values else None


def model_price_dependency_specs(share_factor_type) -> list:
    """The three market inputs, on the option's underlying (``share_factor_type``: its raw factor class) and IRX."""
    from src.domain.entities.factor.dependency_spec import DependencySpec
    from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
    return [
        DependencySpec(factor_type=share_factor_type, group="price", name_in=["close"], source_not_in=["calculated"],
                       lookback=1, key=SPOT),
        DependencySpec(factor_type=share_factor_type, group="price", name_in=["close"], source_not_in=["calculated"],
                       subgroup="OPTION_IMPLIED_VOLATILITY", lookback=1, key=IMPLIED_VOL),
        DependencySpec(factor_type=IndexFactor, group="price", name_in=["close"], source_not_in=["calculated"],
                       lookback=1, key=RATE, entity_symbol=IRX_SYMBOL, entity_type="Index"),
    ]


def option_terms(option) -> Optional[tuple]:
    """(strike, expiry date, 'call' | 'put') of an option entity, or None when a term is unknown."""
    strike = getattr(option, "strike_price", None)
    expiry = getattr(option, "expiry", None)
    if strike is None or not expiry:
        return None
    try:
        expiry_date = expiry if isinstance(expiry, date) else datetime.strptime(str(expiry)[:8], "%Y%m%d").date()
    except ValueError:
        return None
    side = str(getattr(option, "option_type", None) or "").strip().lower()
    side = {"c": "call", "call": "call", "p": "put", "put": "put"}.get(side)
    if side is None:
        return None
    return float(strike), expiry_date, side


def black_scholes_merton(S: float, K: float, r: float, sigma: float, T: float, side: str, q: float = 0.0) -> float:
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if side == "call":
        return S * math.exp(-q * T) * _cdf(d1) - K * math.exp(-r * T) * _cdf(d2)
    return K * math.exp(-r * T) * _cdf(-d2) - S * math.exp(-q * T) * _cdf(-d1)


def model_price(dependencies: dict) -> Optional[float]:
    """The option's model price from the resolved dependencies (see the module docstring), or None."""
    terms = option_terms(dependencies.get("entity"))
    spot = _last(dependencies, SPOT)
    when = dependencies.get("target_date")
    if terms is None or spot is None or spot <= 0 or when is None:
        return None
    strike, expiry, side = terms
    day = when.date() if hasattr(when, "date") else when
    if day >= expiry:
        return max(spot - strike, 0.0) if side == "call" else max(strike - spot, 0.0)
    sigma, irx = _last(dependencies, IMPLIED_VOL), _last(dependencies, RATE)
    if sigma is None or sigma <= 0 or irx is None or strike <= 0:
        return None
    rate = math.log1p(irx / IRX_QUOTE_SCALE)
    value = black_scholes_merton(spot, strike, rate, sigma, (expiry - day).days / 365.0, side)
    return value if math.isfinite(value) and value >= 0 else None
