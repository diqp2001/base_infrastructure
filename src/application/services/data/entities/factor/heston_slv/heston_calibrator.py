"""
HestonCalibrator – calibrate Heston parameters to a market IV surface.

Objective
---------
    min_{v0,kappa,theta,xi,rho}
        sum_{K,T}  w(K,T) * (sigma_Heston(K,T) - sigma_market(K,T))^2

Two-phase strategy
------------------
1. Global search via scipy.optimize.differential_evolution (robust, slow).
2. Local refinement via L-BFGS-B (fast, polishes the global optimum).

Weights
-------
Default: bid-ask spread-adjusted (tighter spread → higher weight).
Alternatives can be provided by subclassing or passing a weight matrix.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import differential_evolution, minimize

from .heston_slv_parameters import HestonParameters
from .heston_pricer import HestonPricer


class HestonCalibrator:
    """
    Calibrate Heston parameters (v0, kappa, theta, xi, rho) to a market surface.

    Parameters
    ----------
    pricer : HestonPricer instance (shared with pricing consumers)
    """

    def __init__(self, pricer: Optional[HestonPricer] = None) -> None:
        self._pricer = pricer or HestonPricer()

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def calibrate(
        self,
        strikes: Sequence[float],
        maturities: Sequence[float],
        market_ivs: Sequence[Sequence[float]],
        S: float,
        r: float = 0.0,
        q: float = 0.0,
        weights: Optional[Sequence[Sequence[float]]] = None,
        initial_params: Optional[HestonParameters] = None,
        bounds: Optional[List[Tuple[float, float]]] = None,
        use_global_search: bool = True,
        seed: int = 42,
    ) -> HestonParameters:
        """
        Calibrate Heston model to market implied volatilities.

        Parameters
        ----------
        strikes       : 1-D sequence of strikes (length nK)
        maturities    : 1-D sequence of maturities in years (length nT)
        market_ivs    : 2-D array-like of shape (nK, nT) with market IVs
        S             : current spot price
        r, q          : rates
        weights       : optional (nK, nT) array of calibration weights
                        (default: uniform 1 everywhere)
        initial_params: starting point for local optimiser (default: sensible guess)
        bounds        : [(lb, ub)] for [v0, kappa, theta, xi, rho]
        use_global_search : whether to run differential_evolution first
        seed          : random seed for differential_evolution

        Returns
        -------
        Calibrated HestonParameters
        """
        Ks    = np.asarray(strikes, dtype=float)
        Ts    = np.asarray(maturities, dtype=float)
        ivs   = np.asarray(market_ivs, dtype=float)         # (nK, nT)
        W     = np.ones_like(ivs) if weights is None else np.asarray(weights, dtype=float)

        bounds_ = bounds or HestonParameters.default_bounds()
        x0      = (initial_params or HestonParameters.default_initial(float(np.nanmean(ivs)), r, q)).to_list()

        def objective(x: np.ndarray) -> float:
            return self._objective(x, Ks, Ts, ivs, W, S, r, q)

        best_x = x0

        if use_global_search:
            result = differential_evolution(
                objective,
                bounds_,
                seed=seed,
                maxiter=300,
                tol=1e-7,
                popsize=15,
                mutation=(0.5, 1.5),
                recombination=0.7,
                polish=True,
                updating="deferred",
            )
            best_x = result.x.tolist()

        # Local refinement
        result_local = minimize(
            objective,
            best_x,
            method="L-BFGS-B",
            bounds=bounds_,
            options={"maxiter": 500, "ftol": 1e-12, "gtol": 1e-8},
        )
        best_x = result_local.x.tolist()

        return HestonParameters.from_list(best_x, r=r, q=q)

    # ------------------------------------------------------------------ #
    #  Objective function                                                   #
    # ------------------------------------------------------------------ #

    def _objective(
        self,
        x: np.ndarray,
        Ks: np.ndarray,
        Ts: np.ndarray,
        market_ivs: np.ndarray,
        weights: np.ndarray,
        S: float,
        r: float,
        q: float,
    ) -> float:
        """Weighted sum of squared IV errors."""
        try:
            params = HestonParameters.from_list(x.tolist(), r=r, q=q)
        except Exception:
            return 1e6

        sse = 0.0
        count = 0
        for j, T in enumerate(Ts):
            for i, K in enumerate(Ks):
                miv = market_ivs[i, j]
                if not math.isfinite(miv) or miv <= 0:
                    continue
                w = float(weights[i, j])
                if w <= 0:
                    continue
                model_iv = self._pricer.implied_vol(S, K, T, params)
                if model_iv is None or not math.isfinite(model_iv):
                    sse += w * 1.0   # penalise failures
                else:
                    sse += w * (model_iv - miv) ** 2
                count += 1

        return sse / max(count, 1)

    # ------------------------------------------------------------------ #
    #  Weight helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def atm_weighted(
        strikes: Sequence[float],
        maturities: Sequence[float],
        S: float,
        atm_width: float = 0.20,
    ) -> np.ndarray:
        """
        Gaussian weights centred at-the-money.

        Parameters
        ----------
        atm_width : standard deviation of ln(K/S) used in weight (default 0.20)
        """
        Ks = np.asarray(strikes, dtype=float)
        Ts = np.asarray(maturities, dtype=float)
        log_m = np.log(Ks / S)  # (nK,)
        W = np.exp(-0.5 * (log_m / atm_width) ** 2)  # (nK,)
        # Broadcast to (nK, nT)
        return np.tile(W[:, None], (1, len(Ts)))

    @staticmethod
    def vega_weighted(
        strikes: Sequence[float],
        maturities: Sequence[float],
        market_ivs: Sequence[Sequence[float]],
        S: float,
        r: float = 0.0,
        q: float = 0.0,
    ) -> np.ndarray:
        """
        Vega-weighted: higher vega → higher weight (emphasises the wing less).
        """
        Ks  = np.asarray(strikes, dtype=float)
        Ts  = np.asarray(maturities, dtype=float)
        ivs = np.asarray(market_ivs, dtype=float)
        W   = np.zeros_like(ivs)
        for i, K in enumerate(Ks):
            for j, T in enumerate(Ts):
                sigma = ivs[i, j]
                if sigma > 0 and T > 0:
                    W[i, j] = HestonPricer.bsm_vega(S, K, r, q, T, sigma)
        total = W.sum()
        return W / total if total > 0 else np.ones_like(ivs)
