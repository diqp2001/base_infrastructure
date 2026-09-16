"""
Market implied-volatility surface abstraction.

Workflow
--------
MarketQuote                 raw tick (strike, maturity, iv, weight)
ImpliedVolatilitySurface    smooth, arb-aware IV interpolation
OptionPriceSurface          call prices + analytical derivatives for Dupire
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.interpolate import RectBivariateSpline, SmoothBivariateSpline
from scipy.stats import norm


# ─────────────────────────────────────────────────────────────────────────── #
#  Raw market quote                                                            #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class MarketQuote:
    """A single market option quote."""
    strike: float
    maturity: float       # years to expiry
    iv: float             # mid implied volatility (annualised)
    option_type: str = "call"
    bid_iv: Optional[float] = None
    ask_iv: Optional[float] = None
    weight: float = 1.0   # calibration weight


# ─────────────────────────────────────────────────────────────────────────── #
#  Black-Scholes helpers                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

def _bsm_call(S: float, K: float, r: float, q: float, T: float, sigma: float) -> float:
    """Black-Scholes-Merton call price."""
    if T <= 0 or sigma <= 0:
        return max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)
    sqT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqT)
    d2 = d1 - sigma * sqT
    return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def _bsm_put(S: float, K: float, r: float, q: float, T: float, sigma: float) -> float:
    call = _bsm_call(S, K, r, q, T, sigma)
    # put-call parity
    return call + K * math.exp(-r * T) - S * math.exp(-q * T)


def _bsm_vega(S: float, K: float, r: float, q: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    sqT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqT)
    return S * math.exp(-q * T) * norm.pdf(d1) * sqT


def iv_from_price(
    price: float,
    S: float,
    K: float,
    r: float,
    q: float,
    T: float,
    option_type: str = "call",
    tol: float = 1e-8,
    max_iter: int = 100,
) -> Optional[float]:
    """Newton-Raphson implied vol inversion."""
    if price <= 0 or T <= 0 or S <= 0 or K <= 0:
        return None
    intrinsic = max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)
    if option_type.lower() == "put":
        intrinsic = max(K * math.exp(-r * T) - S * math.exp(-q * T), 0.0)
    if price < intrinsic - 1e-8:
        return None

    # Initial guess: Brenner-Subrahmanyam ATM approximation or moneyness-based
    log_m = abs(math.log(S / K))
    sqrt_T = math.sqrt(T)
    if log_m < 0.01:
        # ATM: C ≈ S*e^(-qT)*sigma*sqrt(T)/sqrt(2*pi)  →  sigma ≈ C*sqrt(2*pi)/(S*e^(-qT)*sqrt(T))
        denom = S * math.exp(-q * T) * sqrt_T
        sigma = price * math.sqrt(2.0 * math.pi) / denom if denom > 0 else 0.2
    else:
        sigma = math.sqrt(2.0 * log_m / T)
    sigma = max(min(sigma, 5.0), 0.005)

    bsm = _bsm_call if option_type.lower() == "call" else _bsm_put
    for _ in range(max_iter):
        p = bsm(S, K, r, q, T, sigma)
        v = _bsm_vega(S, K, r, q, T, sigma)
        diff = p - price
        if abs(diff) < tol:
            break
        if abs(v) < 1e-12:
            break
        sigma -= diff / v
        sigma = max(sigma, 1e-6)
    return sigma if sigma > 1e-6 else None


# ─────────────────────────────────────────────────────────────────────────── #
#  Implied volatility surface                                                  #
# ─────────────────────────────────────────────────────────────────────────── #

class ImpliedVolatilitySurface:
    """
    Smooth, arb-aware implied-volatility surface built from market quotes.

    Internally stores a RectBivariateSpline on a regular (log-moneyness, T) grid
    so that first/second derivatives are cheap and smooth.

    Parameters
    ----------
    quotes : list of MarketQuote
    S      : spot price at surface reference date
    r, q   : rates used when converting prices → IV or IV → prices
    smooth_factor : passed to SmoothBivariateSpline (larger = smoother)
    """

    def __init__(
        self,
        quotes: List[MarketQuote],
        S: float,
        r: float = 0.0,
        q: float = 0.0,
        smooth_factor: float = 0.0,
    ) -> None:
        self.S = S
        self.r = r
        self.q = q

        self._quotes = [q_ for q_ in quotes if q_.iv > 0 and q_.maturity > 0 and q_.strike > 0]
        if len(self._quotes) < 4:
            raise ValueError("Need at least 4 valid quotes to build an IV surface.")

        self.T_min = min(q.maturity for q in self._quotes)
        self.T_max = max(q.maturity for q in self._quotes)
        self.K_min = min(q.strike   for q in self._quotes)
        self.K_max = max(q.strike   for q in self._quotes)

        self._fit(smooth_factor)

    def _fit(self, smooth_factor: float) -> None:
        """Fit a smooth bivariate spline on (log-moneyness, maturity) space."""
        log_m = np.array([math.log(q.strike / self.S) for q in self._quotes])
        mats  = np.array([q.maturity for q in self._quotes])
        ivs   = np.array([q.iv for q in self._quotes])
        weights = np.array([q.weight for q in self._quotes])

        # Unique sorted maturities and strikes for a regular grid
        unique_T = np.unique(mats)
        unique_m = np.unique(log_m)

        if len(unique_T) >= 3 and len(unique_m) >= 3:
            # Build regular grid via smoothing spline
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    spline = SmoothBivariateSpline(
                        mats, log_m, ivs, w=weights, kx=3, ky=3, s=smooth_factor
                    )
                    self._spline = spline
                    self._grid_mode = "smooth"
                    return
                except Exception:
                    pass

        # Fallback: linear RBF-style nearest-neighbour (deterministic, no spline)
        self._raw_log_m = log_m
        self._raw_mats  = mats
        self._raw_ivs   = ivs
        self._grid_mode = "fallback"

    def iv(self, K: float, T: float) -> float:
        """Interpolated implied volatility at (K, T)."""
        log_m = math.log(max(K, 1e-8) / self.S)
        if self._grid_mode == "smooth":
            val = float(self._spline(T, log_m)[0, 0])
        else:
            # Inverse-distance weighted average
            dists = np.sqrt((self._raw_mats - T)**2 + (self._raw_log_m - log_m)**2)
            eps = 1e-12
            w = 1.0 / (dists + eps)
            val = float(np.dot(w, self._raw_ivs) / w.sum())
        return max(val, 0.001)

    def call_price(self, K: float, T: float) -> float:
        """BSM call price from the smoothed IV surface."""
        return _bsm_call(self.S, K, self.r, self.q, T, self.iv(K, T))

    def grid(
        self,
        strikes: Sequence[float],
        maturities: Sequence[float],
    ) -> np.ndarray:
        """
        Evaluate IV on a (len(strikes), len(maturities)) grid.
        Returns shape (len(strikes), len(maturities)).
        """
        Ks = np.asarray(strikes, dtype=float)
        Ts = np.asarray(maturities, dtype=float)
        out = np.empty((len(Ks), len(Ts)))
        for i, K in enumerate(Ks):
            for j, T in enumerate(Ts):
                out[i, j] = self.iv(K, T)
        return out


# ─────────────────────────────────────────────────────────────────────────── #
#  Option price surface (smooth, with analytic derivatives)                   #
# ─────────────────────────────────────────────────────────────────────────── #

class OptionPriceSurface:
    """
    Smooth call-price surface C(K, T) built from an ImpliedVolatilitySurface.

    Uses a RectBivariateSpline on a dense (K, T) grid so that
    dC/dT, dC/dK and d²C/dK² are available as smooth analytical expressions.

    Parameters
    ----------
    iv_surface    : fitted ImpliedVolatilitySurface
    strike_grid   : 1-D array of strikes (must be sorted, len >= 4)
    maturity_grid : 1-D array of maturities in years (must be sorted, len >= 4)
    spline_order  : spline degree (default 3 – cubic)
    smooth        : smoothing factor for RectBivariateSpline (0 = interpolating)
    """

    def __init__(
        self,
        iv_surface: ImpliedVolatilitySurface,
        strike_grid: np.ndarray,
        maturity_grid: np.ndarray,
        spline_order: int = 3,
        smooth: float = 0.0,
    ) -> None:
        self.iv_surface = iv_surface
        self.K_grid = np.asarray(strike_grid, dtype=float)
        self.T_grid = np.asarray(maturity_grid, dtype=float)
        self.S = iv_surface.S
        self.r = iv_surface.r
        self.q = iv_surface.q

        if len(self.K_grid) < 4 or len(self.T_grid) < 4:
            raise ValueError("Need at least 4 strikes and 4 maturities.")

        self._build_spline(spline_order, smooth)

    def _build_spline(self, k: int, s: float) -> None:
        """Build the underlying C(K, T) bivariate spline."""
        prices = np.empty((len(self.K_grid), len(self.T_grid)))
        for j, T in enumerate(self.T_grid):
            for i, K in enumerate(self.K_grid):
                prices[i, j] = self.iv_surface.call_price(K, T)

        # RectBivariateSpline expects (x, y) = (K, T) with strictly ascending arrays
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._spline = RectBivariateSpline(
                self.K_grid, self.T_grid, prices, kx=k, ky=k, s=s
            )

    # ---- Point evaluations --------------------------------------------------

    def price(self, K: float, T: float) -> float:
        val = float(self._spline(K, T)[0, 0])
        # Enforce call lower bound: C >= max(F - K, 0) * discount
        lb = max(self.S * math.exp(-self.q * T) - K * math.exp(-self.r * T), 0.0)
        return max(val, lb)

    def dC_dT(self, K: float, T: float) -> float:
        return float(self._spline(K, T, dy=1)[0, 0])

    def dC_dK(self, K: float, T: float) -> float:
        return float(self._spline(K, T, dx=1)[0, 0])

    def d2C_dK2(self, K: float, T: float) -> float:
        return float(self._spline(K, T, dx=2)[0, 0])

    # ---- Grid evaluations ---------------------------------------------------

    def price_grid(self) -> np.ndarray:
        """Return call prices on the full (K_grid, T_grid) grid, shape (nK, nT)."""
        return self._spline(self.K_grid, self.T_grid)

    def d2C_dK2_grid(self) -> np.ndarray:
        """Second strike derivative on the full grid; used by Dupire."""
        return self._spline(self.K_grid, self.T_grid, dx=2)
