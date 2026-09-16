"""
HestonParameters – immutable parameter container for the Heston SV model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class HestonParameters:
    """
    Calibrated Heston model parameters.

    Fields
    ------
    v0    : initial variance (sigma_0^2, NOT sigma_0)
    kappa : mean-reversion speed (>0)
    theta : long-run variance (>0)
    xi    : vol-of-vol (>0)
    rho   : spot-variance correlation in (-1, 1)
    r     : risk-free rate (continuously compounded)
    q     : continuous dividend yield
    """

    v0: float
    kappa: float
    theta: float
    xi: float
    rho: float
    r: float = 0.0
    q: float = 0.0

    # ------------------------------------------------------------------ #
    #  Derived quantities                                                   #
    # ------------------------------------------------------------------ #

    @property
    def vol0(self) -> float:
        """Initial instantaneous volatility sqrt(v0)."""
        return self.v0 ** 0.5

    @property
    def long_run_vol(self) -> float:
        """Long-run volatility sqrt(theta)."""
        return self.theta ** 0.5

    def feller_condition(self) -> bool:
        """Return True when 2*kappa*theta >= xi^2 (variance process stays > 0)."""
        return 2.0 * self.kappa * self.theta >= self.xi ** 2

    # ------------------------------------------------------------------ #
    #  Serialisation helpers                                                #
    # ------------------------------------------------------------------ #

    def to_list(self) -> List[float]:
        """Ordered list [v0, kappa, theta, xi, rho] for optimisers."""
        return [self.v0, self.kappa, self.theta, self.xi, self.rho]

    @classmethod
    def from_list(
        cls,
        params: List[float],
        r: float = 0.0,
        q: float = 0.0,
    ) -> "HestonParameters":
        """Reconstruct from optimiser output [v0, kappa, theta, xi, rho]."""
        if len(params) != 5:
            raise ValueError("Expected [v0, kappa, theta, xi, rho].")
        return cls(
            v0=float(params[0]),
            kappa=float(params[1]),
            theta=float(params[2]),
            xi=float(params[3]),
            rho=float(params[4]),
            r=r,
            q=q,
        )

    @classmethod
    def default_bounds(cls) -> List[Tuple[float, float]]:
        """
        Reasonable parameter bounds for calibration optimisers.
        Order: [v0, kappa, theta, xi, rho].
        """
        return [
            (1e-4, 2.0),    # v0 : initial variance
            (1e-2, 20.0),   # kappa : mean-reversion speed
            (1e-4, 2.0),    # theta : long-run variance
            (1e-2, 5.0),    # xi : vol-of-vol
            (-0.999, 0.999),# rho : correlation
        ]

    @classmethod
    def default_initial(cls, atm_vol: float = 0.20, r: float = 0.0, q: float = 0.0) -> "HestonParameters":
        """Sensible starting point for calibration given an ATM volatility guess."""
        v0 = atm_vol ** 2
        return cls(v0=v0, kappa=1.5, theta=v0, xi=0.3, rho=-0.5, r=r, q=q)

    def validate(self) -> None:
        """Raise ValueError if any parameter is outside its admissible range."""
        if self.v0 <= 0:
            raise ValueError(f"v0 must be positive, got {self.v0}")
        if self.kappa <= 0:
            raise ValueError(f"kappa must be positive, got {self.kappa}")
        if self.theta <= 0:
            raise ValueError(f"theta must be positive, got {self.theta}")
        if self.xi <= 0:
            raise ValueError(f"xi must be positive, got {self.xi}")
        if abs(self.rho) >= 1.0:
            raise ValueError(f"rho must be in (-1,1), got {self.rho}")

    def __str__(self) -> str:
        feller = "✓" if self.feller_condition() else "✗"
        return (
            f"HestonParameters("
            f"v0={self.v0:.4f}, kappa={self.kappa:.4f}, theta={self.theta:.4f}, "
            f"xi={self.xi:.4f}, rho={self.rho:.4f}, r={self.r:.4f}, q={self.q:.4f}, "
            f"Feller={feller})"
        )
