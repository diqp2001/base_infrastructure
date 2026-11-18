"""
MODELLED ATM call legs for the dispersion backtest: no historical option prices exist (IBKR keeps no expired
options; the screener's quotes start 2026-11-10), so every premium here is a model value and is labelled so.

For a trade opened at the close of day t, per underlying:
  strike   = ShareOptionFactor.select_atm_strike on a listed-style strike grid around the close (the screener's rule)
  vol      = annualised close-to-close volatility of the last ``vol_window`` daily log returns up to t (no look-ahead)
             x ``vol_multiplier`` (1.0 = realised vol as the implied vol)
  price    = CompanyShareOptionBlackScholesMertonPriceFactor.price(S, K, r, vol, T = calendar days / 365, q)
  bid = ask = price (no bid / ask spread is modelled)
and an ETFShareOptionFactor.Leg for the strategy maths (sizing, premium, payoff).

Known limits (reported with the results): realised volatility carries no implied-correlation premium - the ETF call
is priced from the ETF's own realised vol, so the premium the short index call collects is the realised one only;
no spread; European exercise; dividends only through ``dividend_yield``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import (
    CompanyShareOptionBlackScholesMertonPriceFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    Leg,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_factor import (
    ShareOptionFactor,
)

PRICE_SOURCE = "model:black_scholes_merton(realised vol)"


@dataclass(frozen=True)
class OptionModelConfig:
    vol_window: int = 63                 # daily log returns in the volatility estimate
    vol_multiplier: float = 1.0          # implied / realised vol assumed
    etf_vol_multiplier: float = 1.0      # the same for the ETF leg (> constituents' = an index vol premium)
    risk_free_rate: float = 0.0          # continuously compounded, annual (a research assumption: configured)
    dividend_yield: float = 0.0
    multiplier: float = 100.0            # shares per US equity option contract
    annualisation: int = 252


def strike_step(spot: float) -> float:
    """Listed-style strike spacing: 0.5 under 25, 1 under 200, 5 above (US equity / ETF monthly chains)."""
    if spot < 25:
        return 0.5
    if spot < 200:
        return 1.0
    return 5.0


def strike_grid(spot: float, width: int = 5) -> List[float]:
    step = strike_step(spot)
    centre = round(spot / step) * step
    return [round(centre + k * step, 6) for k in range(-width, width + 1) if centre + k * step > 0]


def realised_vol(closes: pd.Series, as_of, window: int, annualisation: int = 252) -> Optional[float]:
    """Annualised std of the last ``window`` daily log returns ending at ``as_of`` (None when fewer)."""
    s = closes[closes.index <= pd.Timestamp(as_of)].dropna()
    if len(s) < window + 1:
        return None
    r = np.log(s.iloc[-(window + 1):]).diff().dropna()
    v = float(r.std(ddof=1)) * math.sqrt(annualisation)
    return v if np.isfinite(v) and v > 0 else None


class ModelledOptionPricer:

    def __init__(self, config: OptionModelConfig = OptionModelConfig()):
        self.config = config
        self._bsm = CompanyShareOptionBlackScholesMertonPriceFactor()

    def price(self, closes: pd.Series, as_of: date, strike: float, expiry: date, is_etf: bool = False
              ) -> Optional[Tuple[float, float, float]]:
        """(price, spot, vol) of a call struck at ``strike`` at the last close dated <= as_of, expiring at the
        close of ``expiry``; on or after the expiry the intrinsic value. None without a close or enough history."""
        cfg = self.config
        upto = closes[closes.index <= pd.Timestamp(as_of)].dropna()
        if upto.empty:
            return None
        spot, day = float(upto.iloc[-1]), upto.index[-1].date()
        days = (expiry - day).days
        if days <= 0:
            return max(spot - strike, 0.0), spot, 0.0
        vol = realised_vol(upto, day, cfg.vol_window, cfg.annualisation)
        if vol is None:
            return None
        sigma = vol * (cfg.etf_vol_multiplier if is_etf else cfg.vol_multiplier)
        value = self._bsm.price(S=spot, K=strike, r=cfg.risk_free_rate, sigma=sigma, T=days / 365.0,
                                q=cfg.dividend_yield, option_type="call")
        if value is None or not np.isfinite(value):
            return None
        return float(value), spot, sigma

    def atm_call(self, symbol: str, closes: pd.Series, opened: date, expiry: date, weight: float = 1.0,
                 is_etf: bool = False) -> Optional[Leg]:
        """The modelled ATM call leg opened at the close of ``opened``; None without a close that day or enough
        history."""
        upto = closes[closes.index <= pd.Timestamp(opened)].dropna()
        if upto.empty or upto.index[-1].date() != opened or (expiry - opened).days <= 0:
            return None
        spot = float(upto.iloc[-1])
        strike = ShareOptionFactor.select_atm_strike(strike_grid(spot), spot)
        priced = self.price(upto, opened, strike, expiry, is_etf) if strike is not None else None
        if priced is None or priced[0] <= 0:
            return None
        value, _, sigma = priced
        return Leg(symbol=symbol, spot=spot, strike=strike, multiplier=self.config.multiplier, bid=value, ask=value,
                   weight=weight, implied_vol=sigma)

    def mark(self, symbol: str, leg: dict, closes: pd.Series, session: date) -> Optional[float]:
        """The value of an open leg at the latest known close (the cycle's interface, as FactorOptionPricer)."""
        priced = self.price(closes.dropna(), session, leg["strike"], leg["expiry"], leg["is_etf"])
        return priced[0] if priced else None
