"""
Dupire local volatility – calibrated from a smoothed call-price surface.

The Dupire (1994) formula for the local volatility in terms of call prices C(K, T):

    sigma_loc^2(K, T) =
        [ dC/dT  +  (r - q) * K * dC/dK  +  q * C ]
        ──────────────────────────────────────────────
               0.5 * K^2 * d^2C/dK^2

Numerically robust implementation
----------------------------------
* Derivatives are taken from a smooth bivariate spline (OptionPriceSurface) rather than
  from noisy finite differences on raw prices.
* The denominator is clipped to a small positive number to avoid division by zero.
* The result is clipped to [sigma_min, sigma_max] for numerical stability.

LocalVolatilitySurface provides bilinear interpolation of the Dupire grid for use
as a callable sigma_loc(S, t) during MC simulation.
"""

from __future__ import annotations

import math
import warnings
from typing import Optional, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .implied_vol_surface import OptionPriceSurface


# ─────────────────────────────────────────────────────────────────────────── #
#  Dupire calculator                                                           #
# ─────────────────────────────────────────────────────────────────────────── #

class DupireLocalVolatility:
    """
    Compute the Dupire local-volatility surface from a smooth call-price surface.

    Parameters
    ----------
    sigma_min : floor applied to the computed local vol (default 0.5%)
    sigma_max : cap applied to the computed local vol (default 300%)
    """

    def __init__(
        self,
        sigma_min: float = 0.005,
        sigma_max: float = 3.0,
    ) -> None:
        self.sigma_min = sigma_min
        self.sigma_max = sigma_max

    def compute_point(
        self,
        K: float,
        T: float,
        price_surface: OptionPriceSurface,
        denom_floor: float = 1e-8,
    ) -> float:
        """
        Dupire local vol at a single (K, T) point.

        Returns sigma_min if the denominator is degenerate.
        """
        r = price_surface.r
        q = price_surface.q

        dC_dT   = price_surface.dC_dT(K, T)
        dC_dK   = price_surface.dC_dK(K, T)
        d2C_dK2 = price_surface.d2C_dK2(K, T)
        C       = price_surface.price(K, T)

        numerator   = dC_dT + (r - q) * K * dC_dK + q * C
        denominator = 0.5 * K * K * d2C_dK2

        if denominator < denom_floor:
            return self.sigma_min

        var = numerator / denominator
        if var <= 0:
            return self.sigma_min

        sigma = math.sqrt(var)
        return float(np.clip(sigma, self.sigma_min, self.sigma_max))

    def calibrate(
        self,
        price_surface: OptionPriceSurface,
        denom_floor: float = 1e-8,
    ) -> "LocalVolatilitySurface":
        """
        Build a LocalVolatilitySurface on the price_surface's (K, T) grid.
        """
        Ks = price_surface.K_grid
        Ts = price_surface.T_grid

        sigma_grid = np.empty((len(Ks), len(Ts)))
        for i, K in enumerate(Ks):
            for j, T in enumerate(Ts):
                sigma_grid[i, j] = self.compute_point(K, T, price_surface, denom_floor)

        return LocalVolatilitySurface(
            K_grid=Ks,
            T_grid=Ts,
            sigma_grid=sigma_grid,
            sigma_min=self.sigma_min,
            sigma_max=self.sigma_max,
        )


# ─────────────────────────────────────────────────────────────────────────── #
#  Local vol surface representation                                            #
# ─────────────────────────────────────────────────────────────────────────── #

class LocalVolatilitySurface:
    """
    Dupire local-volatility surface stored on a (K, T) grid with interpolation.

    Provides a callable sigma_loc(S, t) for use in MC simulation.

    Parameters
    ----------
    K_grid     : 1-D sorted array of strike values
    T_grid     : 1-D sorted array of maturity values (years)
    sigma_grid : 2-D array of local vols, shape (len(K_grid), len(T_grid))
    sigma_min  : floor for extrapolation (default 0.5%)
    sigma_max  : cap for extrapolation (default 300%)
    """

    def __init__(
        self,
        K_grid: np.ndarray,
        T_grid: np.ndarray,
        sigma_grid: np.ndarray,
        sigma_min: float = 0.005,
        sigma_max: float = 3.0,
    ) -> None:
        self.K_grid     = np.asarray(K_grid, dtype=float)
        self.T_grid     = np.asarray(T_grid, dtype=float)
        self.sigma_grid = np.asarray(sigma_grid, dtype=float)
        self.sigma_min  = sigma_min
        self.sigma_max  = sigma_max

        # Build interpolator; bounds_error=False → nearest-neighbour extrapolation
        self._interp = RegularGridInterpolator(
            (self.K_grid, self.T_grid),
            self.sigma_grid,
            method="linear",
            bounds_error=False,
            fill_value=None,  # nearest-boundary extrapolation
        )

    def __call__(self, S: float, t: float) -> float:
        """Evaluate local vol sigma_loc(S, t)."""
        try:
            val = float(self._interp([[S, t]])[0])
        except Exception:
            # Nearest-boundary fallback
            K_clipped = float(np.clip(S, self.K_grid[0], self.K_grid[-1]))
            T_clipped = float(np.clip(t, self.T_grid[0], self.T_grid[-1]))
            val = float(self._interp([[K_clipped, T_clipped]])[0])
        return float(np.clip(val, self.sigma_min, self.sigma_max))

    def evaluate_grid(
        self,
        S_grid: np.ndarray,
        t_grid: np.ndarray,
    ) -> np.ndarray:
        """
        Evaluate on a meshgrid of (S, t) values.

        Parameters
        ----------
        S_grid : 1-D array of spot values
        t_grid : 1-D array of time values

        Returns
        -------
        2-D array of shape (len(S_grid), len(t_grid))
        """
        Sflat = np.repeat(S_grid, len(t_grid))
        Tflat = np.tile(t_grid, len(S_grid))
        pts   = np.column_stack([Sflat, Tflat])
        vals  = self._interp(pts).reshape(len(S_grid), len(t_grid))
        return np.clip(vals, self.sigma_min, self.sigma_max)

    def smooth(self, sigma: float = 0.5) -> "LocalVolatilitySurface":
        """
        Return a new surface smoothed with a Gaussian filter.

        Useful to remove spike artefacts from the Dupire inversion.
        """
        from scipy.ndimage import gaussian_filter
        smoothed = gaussian_filter(self.sigma_grid, sigma=sigma)
        return LocalVolatilitySurface(
            self.K_grid, self.T_grid, smoothed, self.sigma_min, self.sigma_max
        )

    @property
    def shape(self) -> Tuple[int, int]:
        return self.sigma_grid.shape
