"""
LeverageFunction – L(S, t) = sigma_local(S, t) / sqrt(E[v_t | S_t = S]).

The leverage function ensures that the Heston-SLV model reproduces the market
local-volatility surface exactly in expectation.

It is stored on a 2-D (spot, time) grid and supports:
* linear interpolation inside the grid
* nearest-boundary extrapolation outside
* Gaussian smoothing of the grid to remove artefacts
* relaxed updates:  L_new = alpha * L_calc + (1 - alpha) * L_old
* min/max clipping for numerical stability
"""

from __future__ import annotations

import math
from typing import Callable, Optional, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

from .dupire_local_vol import LocalVolatilitySurface
from .conditional_variance_estimator import ConditionalVarianceEstimator


class LeverageFunction:
    """
    2-D leverage surface L(S, t).

    Parameters
    ----------
    S_grid    : 1-D sorted array of spot levels (length >= 2)
    t_grid    : 1-D sorted array of time values in years (length >= 2)
    L_values  : 2-D array of leverage values, shape (len(S_grid), len(t_grid))
    L_min     : floor (default 0.01)
    L_max     : cap (default 5.0)
    """

    def __init__(
        self,
        S_grid: np.ndarray,
        t_grid: np.ndarray,
        L_values: np.ndarray,
        L_min: float = 0.01,
        L_max: float = 5.0,
    ) -> None:
        self.S_grid   = np.asarray(S_grid,   dtype=float)
        self.t_grid   = np.asarray(t_grid,   dtype=float)
        self.L_values = np.asarray(L_values, dtype=float)
        self.L_min    = L_min
        self.L_max    = L_max

        self._build_interp()

    def _build_interp(self) -> None:
        clipped = np.clip(self.L_values, self.L_min, self.L_max)
        self._interp = RegularGridInterpolator(
            (self.S_grid, self.t_grid),
            clipped,
            method="linear",
            bounds_error=False,
            fill_value=None,
        )

    # ------------------------------------------------------------------ #
    #  Evaluation                                                           #
    # ------------------------------------------------------------------ #

    def __call__(self, S: float, t: float) -> float:
        """Evaluate L(S, t) with boundary clamping."""
        try:
            val = float(self._interp([[S, t]])[0])
        except Exception:
            S_c = float(np.clip(S, self.S_grid[0], self.S_grid[-1]))
            t_c = float(np.clip(t, self.t_grid[0], self.t_grid[-1]))
            val = float(self._interp([[S_c, t_c]])[0])
        return float(np.clip(val, self.L_min, self.L_max))

    def evaluate_vectorized(
        self, S_arr: np.ndarray, t_arr: np.ndarray
    ) -> np.ndarray:
        """
        Vectorized evaluation for arrays of (S, t) pairs.

        Parameters
        ----------
        S_arr : shape (N,)
        t_arr : shape (N,) or scalar

        Returns
        -------
        L values, shape (N,)
        """
        if np.isscalar(t_arr):
            t_arr = np.full_like(S_arr, t_arr)
        pts  = np.column_stack([S_arr, t_arr])
        vals = self._interp(pts)
        return np.clip(vals, self.L_min, self.L_max)

    # ------------------------------------------------------------------ #
    #  Updates                                                              #
    # ------------------------------------------------------------------ #

    def smooth(self, sigma: float = 1.0) -> "LeverageFunction":
        """Return a new LeverageFunction with Gaussian-smoothed L values."""
        smoothed = gaussian_filter(self.L_values, sigma=sigma)
        return LeverageFunction(self.S_grid, self.t_grid, smoothed, self.L_min, self.L_max)

    def blend(self, other: "LeverageFunction", alpha: float) -> "LeverageFunction":
        """
        Relaxed update: L = alpha * other + (1 - alpha) * self.

        Parameters
        ----------
        other : newly calculated leverage function
        alpha : relaxation factor in (0, 1];  alpha=1 → full update
        """
        if alpha <= 0 or alpha > 1:
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        # Interpolate `other` onto self's grid so different grid sizes are handled.
        SS, TT = np.meshgrid(self.S_grid, self.t_grid, indexing="ij")
        other_on_self = other.evaluate_vectorized(SS.ravel(), TT.ravel()).reshape(SS.shape)
        new_vals = alpha * other_on_self + (1.0 - alpha) * self.L_values
        return LeverageFunction(self.S_grid, self.t_grid, new_vals, self.L_min, self.L_max)

    def max_abs_diff(self, other: "LeverageFunction") -> float:
        """L_inf distance from another LeverageFunction (for convergence check)."""
        return float(np.max(np.abs(self.L_values - other.L_values)))

    # ------------------------------------------------------------------ #
    #  Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def identity(
        cls,
        S_grid: np.ndarray,
        t_grid: np.ndarray,
        L_min: float = 0.01,
        L_max: float = 5.0,
    ) -> "LeverageFunction":
        """Start with L(S, t) = 1 everywhere (pure Heston, no leverage)."""
        return cls(
            S_grid,
            t_grid,
            np.ones((len(S_grid), len(t_grid))),
            L_min,
            L_max,
        )

    @classmethod
    def from_surfaces(
        cls,
        local_vol_surface: LocalVolatilitySurface,
        cve: ConditionalVarianceEstimator,
        S_particles: np.ndarray,
        v_particles: np.ndarray,
        t_grid: np.ndarray,
        S_grid: np.ndarray,
        S_paths_by_time: Optional[np.ndarray] = None,
        v_paths_by_time: Optional[np.ndarray] = None,
        L_min: float = 0.01,
        L_max: float = 5.0,
    ) -> "LeverageFunction":
        """
        Compute the leverage function from a local-vol surface and particle cloud.

        Parameters
        ----------
        local_vol_surface : calibrated LocalVolatilitySurface
        cve               : ConditionalVarianceEstimator
        S_particles       : spot particles at the LAST simulation time (1-D, N)
        v_particles       : variance particles at the LAST simulation time (1-D, N)
        t_grid            : 1-D time grid (same as used for SLV simulation)
        S_grid            : 1-D spot grid for the leverage surface
        S_paths_by_time   : optional 3-D array (n_t, n_particles) with per-time
                            particle spots; if provided, per-time conditional variance
                            is estimated at each t in t_grid
        v_paths_by_time   : corresponding 3-D variance particles
        """
        nS = len(S_grid)
        nT = len(t_grid)
        L_vals = np.ones((nS, nT))

        for j, t in enumerate(t_grid):
            if t <= 0:
                continue

            # Per-time particles if available, else reuse the terminal cloud
            if S_paths_by_time is not None and v_paths_by_time is not None:
                Sp = S_paths_by_time[j]
                Vp = v_paths_by_time[j]
            else:
                Sp = S_particles
                Vp = v_particles

            # Conditional variance on S_grid
            cond_v = cve.estimate_on_grid(S_grid, Sp, Vp)

            for i, S in enumerate(S_grid):
                sigma_l = local_vol_surface(S, t)
                cv      = cond_v[i]
                if cv > 0 and sigma_l > 0:
                    L_vals[i, j] = sigma_l / math.sqrt(cv)
                # else leave at 1.0

        return cls(S_grid, t_grid, L_vals, L_min, L_max)
