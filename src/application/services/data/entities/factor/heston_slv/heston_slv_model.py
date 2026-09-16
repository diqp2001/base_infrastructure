"""
Heston-SLV Model – Monte Carlo simulation and iterative calibration.

Dynamics
--------
    dS_t = (r - q) S_t dt  +  L(S_t, t) sqrt(v_t) S_t dW_t^S
    dv_t = kappa(theta - v_t) dt  +  xi sqrt(v_t) dW_t^v
    corr(dW^S, dW^v) = rho dt

The leverage function L(S, t) is determined by the fixed-point condition

    L(S, t)^2 = sigma_local(S, t)^2 / E[v_t | S_t = S]

Calibration workflow (HestonSLVCalibrator)
------------------------------------------
1.  Calibrate Heston parameters to market IVs.
2.  Compute Dupire local-vol surface from smoothed market prices.
3.  Initialise L(S, t) = 1.
4.  Simulate n_particles under the current SLV dynamics.
5.  Estimate E[v_t | S_t] via kernel smoother.
6.  Update L(S, t) using the fixed-point formula.
7.  Smooth and relax: L ← alpha * L_new + (1-alpha) * L_old.
8.  Repeat 4-7 until convergence or max_iter is reached.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .heston_slv_parameters import HestonParameters
from .heston_pricer import HestonPricer
from .heston_calibrator import HestonCalibrator
from .heston_simulator import HestonSimulator
from .implied_vol_surface import ImpliedVolatilitySurface, OptionPriceSurface, MarketQuote
from .dupire_local_vol import DupireLocalVolatility, LocalVolatilitySurface
from .conditional_variance_estimator import ConditionalVarianceEstimator
from .leverage_function import LeverageFunction


# ─────────────────────────────────────────────────────────────────────────── #
#  Configuration                                                               #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class HestonSLVConfig:
    """Calibration hyper-parameters for HestonSLVCalibrator."""

    max_iter: int             = 5        # max outer fixed-point iterations
    tol: float                = 1e-4    # convergence tolerance (L_inf of delta L)
    n_particles: int          = 5_000   # MC paths for leverage estimation
    n_steps_per_year: int     = 52      # time steps per year in calibration MC
    n_spot_grid: int          = 60      # number of spot grid points for L surface
    n_time_grid: int          = 20      # number of time grid points for L surface
    bandwidth: Optional[float] = None   # kernel bandwidth (None → Silverman rule)
    relax_alpha: float        = 0.7     # relaxation factor for L update
    smooth_sigma: float       = 1.0     # Gaussian smoother sigma for L surface
    L_min: float              = 0.01    # leverage floor
    L_max: float              = 5.0     # leverage cap
    seed: int                 = 42      # RNG seed
    spot_grid_width: float    = 0.5     # ± ln(S) from spot_0 for S_grid


# ─────────────────────────────────────────────────────────────────────────── #
#  HestonSLV Monte Carlo simulator                                             #
# ─────────────────────────────────────────────────────────────────────────── #

class HestonSLVSimulator:
    """
    Numpy-vectorized SLV Monte Carlo.

    Variance scheme: Full Truncation Euler.
    Spot scheme:     Log-Euler with L(S_t, t) * sqrt(v_t) vol.
    """

    def simulate(
        self,
        params: HestonParameters,
        leverage: LeverageFunction,
        S0: float,
        T: float,
        n_paths: int = 10_000,
        n_steps: int = 252,
        seed: Optional[int] = None,
        record_times: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, Optional[List[Tuple[np.ndarray, np.ndarray]]]]:
        """
        Simulate Heston-SLV paths.

        Parameters
        ----------
        params        : HestonParameters
        leverage      : LeverageFunction  L(S, t)
        S0            : initial spot
        T             : simulation horizon (years)
        n_paths       : number of Monte Carlo paths
        n_steps       : total time steps (dt = T / n_steps)
        seed          : RNG seed
        record_times  : optional 1-D array of times at which to record
                        (S_t, v_t) particle states; used during calibration

        Returns
        -------
        S_T       : terminal spots, shape (n_paths,)
        v_T       : terminal variances, shape (n_paths,)
        snapshots : list of (S_t, v_t) at each record_time, or None
        """
        rng    = np.random.default_rng(seed)
        dt     = T / n_steps
        sqrt_dt = math.sqrt(dt)

        kappa = params.kappa
        theta = params.theta
        xi    = params.xi
        rho   = params.rho
        r, q  = params.r, params.q
        rho_perp = math.sqrt(max(1.0 - rho * rho, 0.0))

        S = np.full(n_paths, S0, dtype=float)
        v = np.full(n_paths, params.v0, dtype=float)

        # Build a sorted index of record steps
        snapshots: Optional[List[Tuple[np.ndarray, np.ndarray]]] = None
        record_steps: Optional[set] = None
        if record_times is not None:
            record_steps = {
                min(max(int(round(t / dt)), 0), n_steps)
                for t in record_times
                if 0 < t <= T
            }
            snapshots = []

        for step in range(n_steps):
            t_now = step * dt

            Z_S    = rng.standard_normal(n_paths)
            Z_perp = rng.standard_normal(n_paths)
            Z_v    = rho * Z_S + rho_perp * Z_perp

            v_plus = np.maximum(v, 0.0)
            sqrt_v = np.sqrt(v_plus)

            # Leverage evaluated at current (S, t)
            L = leverage.evaluate_vectorized(S, t_now)

            # Log-Euler spot update with leverage
            vol_eff = L * sqrt_v                       # effective vol
            S = S * np.exp(
                (r - q - 0.5 * vol_eff ** 2) * dt
                + vol_eff * sqrt_dt * Z_S
            )
            S = np.maximum(S, 1e-10)

            # Full Truncation Euler for variance
            v = v + kappa * (theta - v_plus) * dt + xi * sqrt_v * sqrt_dt * Z_v
            v = np.maximum(v, 0.0)

            # Record snapshot if requested
            if record_steps and (step + 1) in record_steps:
                snapshots.append((S.copy(), v.copy()))

        return S, v, snapshots

    def price(
        self,
        params: HestonParameters,
        leverage: LeverageFunction,
        S0: float,
        K: float,
        T: float,
        option_type: str = "call",
        n_paths: int = 20_000,
        n_steps: int = 252,
        seed: Optional[int] = None,
    ) -> Optional[float]:
        """Monte Carlo SLV call (or put) price."""
        if S0 <= 0 or K <= 0 or T <= 0:
            return None
        try:
            S_T, _, _ = self.simulate(params, leverage, S0, T, n_paths, n_steps, seed)
            r = params.r
            if option_type.lower() == "call":
                payoffs = np.maximum(S_T - K, 0.0)
            else:
                payoffs = np.maximum(K - S_T, 0.0)
            return float(math.exp(-r * T) * payoffs.mean())
        except Exception:
            return None

    def implied_vol(
        self,
        params: HestonParameters,
        leverage: LeverageFunction,
        S0: float,
        K: float,
        T: float,
        option_type: str = "call",
        n_paths: int = 20_000,
        n_steps: int = 252,
        seed: Optional[int] = None,
    ) -> Optional[float]:
        """Implied vol of the SLV MC price (BSM inversion)."""
        p = self.price(params, leverage, S0, K, T, option_type, n_paths, n_steps, seed)
        if p is None:
            return None
        from .implied_vol_surface import iv_from_price
        return iv_from_price(p, S0, K, params.r, params.q, T, option_type)


# ─────────────────────────────────────────────────────────────────────────── #
#  Iterative SLV calibration                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

class HestonSLVCalibrator:
    """
    Fixed-point iterative calibration of the Heston-SLV model.

    Usage
    -----
    >>> calibrator = HestonSLVCalibrator()
    >>> model = calibrator.calibrate(quotes, S0, r, q, config)
    >>> price = model.price(S0, K, T)
    """

    def __init__(self) -> None:
        self._pricer     = HestonPricer()
        self._heston_cal = HestonCalibrator(self._pricer)
        self._slv_sim    = HestonSLVSimulator()
        self._dupire     = DupireLocalVolatility()
        self._cve        = ConditionalVarianceEstimator()

    def calibrate(
        self,
        quotes: List[MarketQuote],
        S0: float,
        r: float = 0.0,
        q: float = 0.0,
        config: Optional[HestonSLVConfig] = None,
        heston_params: Optional[HestonParameters] = None,
    ) -> "HestonSLVModel":
        """
        Full SLV calibration pipeline.

        Parameters
        ----------
        quotes        : list of MarketQuote objects
        S0            : current spot
        r, q          : rates
        config        : HestonSLVConfig (defaults used if None)
        heston_params : pre-calibrated Heston params (skip Heston calibration if provided)

        Returns
        -------
        Calibrated HestonSLVModel ready for pricing.
        """
        cfg = config or HestonSLVConfig()

        # ── Step 1: calibrate Heston to market IVs ────────────────────── #
        if heston_params is None:
            heston_params = self._calibrate_heston(quotes, S0, r, q)

        # ── Step 2: build smoothed price surface + Dupire local vol ───── #
        iv_surface    = self._build_iv_surface(quotes, S0, r, q)
        price_surface = self._build_price_surface(iv_surface, S0, cfg)
        lv_surface    = self._dupire.calibrate(price_surface)

        # ── Step 3: set up grids ──────────────────────────────────────── #
        T_max        = max(q_.maturity for q_ in quotes)
        t_grid       = np.linspace(0.0, T_max, cfg.n_time_grid + 1)[1:]   # exclude t=0
        w            = cfg.spot_grid_width
        log_S_grid   = np.linspace(-w, w, cfg.n_spot_grid)
        S_grid       = S0 * np.exp(log_S_grid)
        n_steps_total = max(int(cfg.n_steps_per_year * T_max), 1)
        record_times  = t_grid   # record particle snapshots at each t_grid point

        # ── Step 4: initialise leverage as identity ───────────────────── #
        leverage = LeverageFunction.identity(S_grid, t_grid, cfg.L_min, cfg.L_max)

        converged   = False
        diagnostics: List[float] = []

        for iteration in range(cfg.max_iter):
            # ── Simulate SLV paths ─────────────────────────────────────── #
            _, _, snapshots = self._slv_sim.simulate(
                params       = heston_params,
                leverage     = leverage,
                S0           = S0,
                T            = T_max,
                n_paths      = cfg.n_particles,
                n_steps      = n_steps_total,
                seed         = cfg.seed + iteration,
                record_times = record_times,
            )

            # ── Estimate E[v_t | S_t] and compute new leverage ─────────── #
            new_L_vals = np.ones_like(leverage.L_values)

            for j, (t, snap) in enumerate(zip(t_grid, snapshots or [])):
                S_p, v_p = snap
                bw = (
                    cfg.bandwidth
                    if cfg.bandwidth is not None
                    else ConditionalVarianceEstimator.silverman_bandwidth(S_p)
                )
                cve_j = ConditionalVarianceEstimator(bandwidth=bw, floor=1e-8)
                cond_v = cve_j.estimate_on_grid(S_grid, S_p, v_p)

                for i, S in enumerate(S_grid):
                    sigma_l = lv_surface(S, t)
                    cv      = cond_v[i]
                    if cv > 0 and sigma_l > 0:
                        new_L_vals[i, j] = sigma_l / math.sqrt(cv)

            # ── Build, smooth and relax ────────────────────────────────── #
            new_leverage = LeverageFunction(
                S_grid, t_grid, new_L_vals, cfg.L_min, cfg.L_max
            ).smooth(cfg.smooth_sigma)

            blended = leverage.blend(new_leverage, cfg.relax_alpha)
            delta   = leverage.max_abs_diff(blended)
            diagnostics.append(delta)

            leverage = blended

            if delta < cfg.tol:
                converged = True
                break

        return HestonSLVModel(
            heston_params  = heston_params,
            leverage       = leverage,
            lv_surface     = lv_surface,
            iv_surface     = iv_surface,
            simulator      = self._slv_sim,
            converged      = converged,
            n_iterations   = len(diagnostics),
            diagnostics    = diagnostics,
        )

    # ── Internal helpers ───────────────────────────────────────────────── #

    def _calibrate_heston(
        self,
        quotes: List[MarketQuote],
        S0: float,
        r: float,
        q: float,
    ) -> HestonParameters:
        """Calibrate Heston params from the market quotes."""
        strikes    = sorted({qq.strike   for qq in quotes})
        maturities = sorted({qq.maturity for qq in quotes})

        ivs     = np.full((len(strikes), len(maturities)), np.nan)
        weights = np.ones_like(ivs)

        K_idx = {K: i for i, K in enumerate(strikes)}
        T_idx = {T: j for j, T in enumerate(maturities)}
        for qq in quotes:
            i = K_idx[qq.strike]
            j = T_idx[qq.maturity]
            ivs[i, j]     = qq.iv
            weights[i, j] = qq.weight

        mask = np.isfinite(ivs) & (ivs > 0)
        if not mask.any():
            return HestonParameters.default_initial(0.20, r, q)

        atm_iv = float(np.nanmedian(ivs))
        return self._heston_cal.calibrate(
            strikes, maturities, ivs, S0, r, q, weights
        )

    def _build_iv_surface(
        self, quotes: List[MarketQuote], S0: float, r: float, q: float
    ) -> ImpliedVolatilitySurface:
        return ImpliedVolatilitySurface(quotes, S0, r, q, smooth_factor=0.0)

    def _build_price_surface(
        self,
        iv_surface: ImpliedVolatilitySurface,
        S0: float,
        cfg: HestonSLVConfig,
    ) -> OptionPriceSurface:
        w = cfg.spot_grid_width
        K_grid = S0 * np.exp(np.linspace(-w, w, cfg.n_spot_grid))
        T_max  = iv_surface.T_max if hasattr(iv_surface, "T_max") else 2.0
        T_grid = np.linspace(0.01, T_max, cfg.n_time_grid)
        # Build price surface with smoothing spline
        return OptionPriceSurface(iv_surface, K_grid, T_grid, spline_order=3, smooth=0.0)


# ─────────────────────────────────────────────────────────────────────────── #
#  Calibrated model – pricing interface                                        #
# ─────────────────────────────────────────────────────────────────────────── #

class HestonSLVModel:
    """
    Calibrated Heston-SLV model.

    Wraps the Heston parameters and leverage function and exposes a
    price() / implied_vol() interface for downstream use.
    """

    def __init__(
        self,
        heston_params: HestonParameters,
        leverage: LeverageFunction,
        lv_surface: LocalVolatilitySurface,
        iv_surface: ImpliedVolatilitySurface,
        simulator: Optional[HestonSLVSimulator] = None,
        converged: bool = False,
        n_iterations: int = 0,
        diagnostics: Optional[List[float]] = None,
    ) -> None:
        self.heston_params  = heston_params
        self.leverage       = leverage
        self.lv_surface     = lv_surface
        self.iv_surface     = iv_surface
        self._simulator     = simulator or HestonSLVSimulator()
        self.converged      = converged
        self.n_iterations   = n_iterations
        self.diagnostics    = diagnostics or []

    def price(
        self,
        S0: float,
        K: float,
        T: float,
        option_type: str = "call",
        n_paths: int = 20_000,
        n_steps: int = 252,
        seed: Optional[int] = None,
    ) -> Optional[float]:
        """Monte Carlo SLV European option price."""
        return self._simulator.price(
            self.heston_params, self.leverage,
            S0, K, T, option_type, n_paths, n_steps, seed,
        )

    def implied_vol(
        self,
        S0: float,
        K: float,
        T: float,
        option_type: str = "call",
        n_paths: int = 20_000,
        n_steps: int = 252,
        seed: Optional[int] = None,
    ) -> Optional[float]:
        """BSM implied vol of the SLV Monte Carlo price."""
        return self._simulator.implied_vol(
            self.heston_params, self.leverage,
            S0, K, T, option_type, n_paths, n_steps, seed,
        )

    def heston_price(
        self, S0: float, K: float, T: float, option_type: str = "call"
    ) -> Optional[float]:
        """Semi-analytic Heston price (ignores leverage, for comparison)."""
        return HestonPricer().price(S0, K, T, self.heston_params, option_type)

    def heston_iv(
        self, S0: float, K: float, T: float, option_type: str = "call"
    ) -> Optional[float]:
        """Heston implied vol for comparison with SLV and market."""
        return HestonPricer().implied_vol(S0, K, T, self.heston_params, option_type)

    def __repr__(self) -> str:
        return (
            f"HestonSLVModel(converged={self.converged}, "
            f"n_iter={self.n_iterations}, "
            f"params={self.heston_params})"
        )
