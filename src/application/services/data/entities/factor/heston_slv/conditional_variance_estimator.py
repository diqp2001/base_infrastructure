"""
ConditionalVarianceEstimator – Gaussian kernel estimator for E[v_t | S_t = S].

For a set of Monte Carlo particles (S_i, v_i) at time t, the conditional
expectation is approximated by:

    E[v_t | S_t = S]  ≈  Σ_i v_i * K(S_i, S, h)  /  Σ_i K(S_i, S, h)

where the Gaussian kernel in log-spot space is:

    K(S_i, S, h) = exp( -( ln(S_i/S) )^2 / (2 h^2) )

Numerical robustness
--------------------
* Log-spot coordinates remove the positive-support constraint on S.
* A minimum effective-particle count prevents estimates in empty regions.
* A fallback (marginal variance mean) is returned when the denominator is tiny.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy.interpolate import interp1d


class ConditionalVarianceEstimator:
    """
    Nadaraya-Watson kernel estimator for the conditional variance E[v | S].

    Parameters
    ----------
    bandwidth      : Gaussian kernel bandwidth in log-spot space (default 0.05)
    min_eff_count  : minimum effective particle count; if below this threshold
                     the estimator returns the unconditional mean (default 10)
    floor          : minimum returned conditional variance (prevents negative vals)
    """

    def __init__(
        self,
        bandwidth: float = 0.05,
        min_eff_count: float = 10.0,
        floor: float = 1e-6,
    ) -> None:
        self.bandwidth      = bandwidth
        self.min_eff_count  = min_eff_count
        self.floor          = floor

    # ------------------------------------------------------------------ #
    #  Single-point estimate                                               #
    # ------------------------------------------------------------------ #

    def estimate_point(
        self,
        S_query: float,
        S_particles: np.ndarray,
        v_particles: np.ndarray,
    ) -> float:
        """
        Estimate E[v | S = S_query] from a cloud of particles.

        Parameters
        ----------
        S_query    : spot level at which to evaluate
        S_particles : 1-D array of particle spot values
        v_particles : 1-D array of particle variance values (same length)

        Returns
        -------
        Conditional variance estimate (>= floor).
        """
        if S_query <= 0:
            return float(np.mean(v_particles))

        log_diffs = np.log(S_particles / S_query)
        h = self.bandwidth
        weights  = np.exp(-0.5 * (log_diffs / h) ** 2)
        w_sum    = weights.sum()
        eff_n    = w_sum ** 2 / (weights ** 2).sum() if (weights ** 2).sum() > 0 else 0.0

        if w_sum < 1e-15 or eff_n < self.min_eff_count:
            # Not enough nearby particles → fall back to unconditional mean
            return max(float(np.mean(v_particles)), self.floor)

        cond_var = float(np.dot(weights, v_particles) / w_sum)
        return max(cond_var, self.floor)

    # ------------------------------------------------------------------ #
    #  Grid estimate                                                        #
    # ------------------------------------------------------------------ #

    def estimate_on_grid(
        self,
        S_grid: np.ndarray,
        S_particles: np.ndarray,
        v_particles: np.ndarray,
        bandwidth: Optional[float] = None,
    ) -> np.ndarray:
        """
        Estimate E[v | S] for every point in S_grid.

        Returns a 1-D array of shape (len(S_grid),).
        """
        h = bandwidth if bandwidth is not None else self.bandwidth
        log_S = np.log(S_particles)           # (N,)
        log_g = np.log(S_grid)                # (G,)

        # Broadcasting: (G, N) kernel matrix
        log_diff = log_g[:, None] - log_S[None, :]    # (G, N)
        W = np.exp(-0.5 * (log_diff / h) ** 2)        # (G, N)

        w_sum  = W.sum(axis=1)                         # (G,)
        wv_sum = (W * v_particles[None, :]).sum(axis=1) # (G,)

        # Effective particle counts per grid point
        eff_n  = w_sum ** 2 / np.maximum((W ** 2).sum(axis=1), 1e-30)

        uncond_mean = float(np.mean(v_particles))
        cond_var    = np.where(
            (w_sum > 1e-15) & (eff_n >= self.min_eff_count),
            wv_sum / np.maximum(w_sum, 1e-30),
            uncond_mean,
        )
        return np.maximum(cond_var, self.floor)

    # ------------------------------------------------------------------ #
    #  Bandwidth selection (Silverman's rule of thumb)                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def silverman_bandwidth(S_particles: np.ndarray, n_dim: int = 1) -> float:
        """
        Silverman's rule-of-thumb bandwidth for log-spot particles.

        h = 1.06 * std(log S) * N^{-1/(2*d+4)}   (Gaussian kernel, d=1 here)
        """
        log_S = np.log(S_particles)
        N = len(log_S)
        if N < 2:
            return 0.05
        std = float(np.std(log_S, ddof=1))
        return 1.06 * std * N ** (-1.0 / (2 * n_dim + 4))

    # ------------------------------------------------------------------ #
    #  Callable interface (for use with LeverageFunction)                  #
    # ------------------------------------------------------------------ #

    def build_interpolant(
        self,
        S_grid: np.ndarray,
        S_particles: np.ndarray,
        v_particles: np.ndarray,
        bandwidth: Optional[float] = None,
    ) -> interp1d:
        """
        Build a 1-D interpolant E[v | S] over S_grid.

        Returns a scipy interp1d callable (linear, extrapolation = boundary value).
        """
        cond_vals = self.estimate_on_grid(S_grid, S_particles, v_particles, bandwidth)
        return interp1d(
            S_grid,
            cond_vals,
            kind="linear",
            bounds_error=False,
            fill_value=(cond_vals[0], cond_vals[-1]),
        )
