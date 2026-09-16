"""
HestonSimulator – numpy-vectorized Monte Carlo for the Heston model.

Variance scheme: Full Truncation Euler (Lord et al., 2010).
The design makes it straightforward to substitute the Andersen QE scheme later
by swapping _full_truncation_euler for a different method.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np

from .heston_slv_parameters import HestonParameters


class HestonSimulator:
    """
    Vectorized Heston Monte Carlo simulator.

    All paths are propagated simultaneously via numpy array operations to avoid
    Python loops over individual particles.

    Parameters
    ----------
    n_paths : number of Monte Carlo paths (default 10_000)
    n_steps : number of time steps (default 252 per year; override with dt)
    seed    : RNG seed for reproducibility (None → non-deterministic)
    """

    def __init__(
        self,
        n_paths: int = 10_000,
        n_steps: int = 252,
        seed: Optional[int] = None,
    ) -> None:
        self.n_paths = n_paths
        self.n_steps = n_steps
        self.seed = seed

    # ------------------------------------------------------------------ #
    #  Core simulation engine                                              #
    # ------------------------------------------------------------------ #

    def simulate(
        self,
        params: HestonParameters,
        S0: float,
        T: float,
        return_paths: bool = False,
        n_paths: Optional[int] = None,
        n_steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate Heston paths using Full Truncation Euler.

        Returns
        -------
        S_paths : shape (n_paths,) if return_paths=False, else (n_paths, n_steps+1)
                  Final (or all) spot values.
        v_paths : same shape, variance process values.
        """
        n_paths_ = n_paths or self.n_paths
        n_steps_ = n_steps or self.n_steps
        seed_    = seed if seed is not None else self.seed

        rng = np.random.default_rng(seed_)
        dt = T / n_steps_
        sqrt_dt = math.sqrt(dt)

        kappa = params.kappa
        theta = params.theta
        xi    = params.xi
        rho   = params.rho
        r, q  = params.r, params.q

        if return_paths:
            S_all = np.empty((n_paths_, n_steps_ + 1))
            v_all = np.empty((n_paths_, n_steps_ + 1))
            S_all[:, 0] = S0
            v_all[:, 0] = params.v0

        S = np.full(n_paths_, S0, dtype=float)
        v = np.full(n_paths_, params.v0, dtype=float)

        for step in range(n_steps_):
            # Correlated normals: Z_v = rho*Z_S + sqrt(1-rho^2)*Z_perp
            Z_S   = rng.standard_normal(n_paths_)
            Z_perp = rng.standard_normal(n_paths_)
            Z_v   = rho * Z_S + math.sqrt(1.0 - rho * rho) * Z_perp

            v_plus = np.maximum(v, 0.0)       # Full Truncation: use v+ for diffusion
            sqrt_v = np.sqrt(v_plus)

            # Spot: log-Euler for positivity
            S = S * np.exp(
                (r - q - 0.5 * v_plus) * dt
                + sqrt_v * sqrt_dt * Z_S
            )

            # Variance: Full Truncation Euler
            v = v + kappa * (theta - v_plus) * dt + xi * sqrt_v * sqrt_dt * Z_v
            v = np.maximum(v, 0.0)            # Absorb at zero

            if return_paths:
                S_all[:, step + 1] = S
                v_all[:, step + 1] = v

        if return_paths:
            return S_all, v_all
        return S, v

    # ------------------------------------------------------------------ #
    #  Pricing                                                             #
    # ------------------------------------------------------------------ #

    def price(
        self,
        params: HestonParameters,
        S0: float,
        K: float,
        T: float,
        option_type: str = "call",
        n_paths: Optional[int] = None,
        n_steps: Optional[int] = None,
        seed: Optional[int] = None,
        antithetic: bool = True,
    ) -> Optional[float]:
        """
        Monte Carlo European option price under Heston.

        Uses antithetic variates by default for variance reduction.
        """
        if S0 <= 0 or K <= 0 or T <= 0 or params.v0 <= 0:
            return None

        try:
            n = (n_paths or self.n_paths) // 2 if antithetic else (n_paths or self.n_paths)
            s_ = seed if seed is not None else self.seed

            rng = np.random.default_rng(s_)
            n_st = n_steps or self.n_steps
            dt = T / n_st
            sqrt_dt = math.sqrt(dt)

            kappa = params.kappa
            theta = params.theta
            xi    = params.xi
            rho   = params.rho
            r, q  = params.r, params.q

            S    = np.full(n, S0, dtype=float)
            v    = np.full(n, params.v0, dtype=float)
            S_a  = np.full(n, S0, dtype=float)  # antithetic
            v_a  = np.full(n, params.v0, dtype=float)

            for _ in range(n_st):
                Z_S    = rng.standard_normal(n)
                Z_perp = rng.standard_normal(n)
                Z_v    = rho * Z_S + math.sqrt(1.0 - rho * rho) * Z_perp

                # Regular path
                vp = np.maximum(v, 0.0)
                sv = np.sqrt(vp)
                S  = S  * np.exp((r - q - 0.5 * vp) * dt + sv * sqrt_dt * Z_S)
                v  = np.maximum(v  + kappa * (theta - vp) * dt + xi * sv * sqrt_dt * Z_v, 0.0)

                # Antithetic path (negate both noise terms)
                vp_a = np.maximum(v_a, 0.0)
                sv_a = np.sqrt(vp_a)
                S_a  = S_a * np.exp((r - q - 0.5 * vp_a) * dt - sv_a * sqrt_dt * Z_S)
                v_a  = np.maximum(v_a + kappa * (theta - vp_a) * dt - xi * sv_a * sqrt_dt * Z_v, 0.0)

            if option_type.lower() == "call":
                payoffs   = np.maximum(S   - K, 0.0)
                payoffs_a = np.maximum(S_a - K, 0.0)
            else:
                payoffs   = np.maximum(K - S,   0.0)
                payoffs_a = np.maximum(K - S_a, 0.0)

            mean_payoff = 0.5 * (payoffs.mean() + payoffs_a.mean())
            return float(math.exp(-r * T) * mean_payoff)

        except Exception:
            return None

    def implied_vol(
        self,
        params: HestonParameters,
        S0: float,
        K: float,
        T: float,
        option_type: str = "call",
        n_paths: Optional[int] = None,
        n_steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Optional[float]:
        """Implied volatility of the Heston MC price (BSM inversion)."""
        mc_price = self.price(params, S0, K, T, option_type, n_paths, n_steps, seed)
        if mc_price is None:
            return None
        from .implied_vol_surface import iv_from_price
        return iv_from_price(mc_price, S0, K, params.r, params.q, T, option_type)
