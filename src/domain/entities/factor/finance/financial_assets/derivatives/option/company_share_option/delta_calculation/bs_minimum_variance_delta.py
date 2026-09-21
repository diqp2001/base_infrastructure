"""BSMinimumVarianceDelta — Hull & White (2017) minimum-variance delta.

Reference
---------
Hull, J. & White, A. (2017). "Optimal Delta Hedging for Options."
Journal of Banking & Finance, 82, 180–190.

Formula
-------
The minimum-variance (MV) delta corrects the standard BS delta by a quadratic
function of δ_BS weighted by φ(d₁) — the normalised vega sensitivity:

    δ_MV = δ_BS + φ(d₁) · exp(-q·T) · (a + b·δ_BS + c·δ_BS²)

where:
  δ_BS = exp(-q·T) · N(d₁)                   (call; N(d₁)-1 for put)
  φ(d₁) = standard normal PDF evaluated at d₁
  a, b, c = quadratic coefficients fitted from realised hedge P&L

With a = b = c = 0 the formula collapses exactly to δ_BS.

Coefficient Fitting
-------------------
`fit_quadratic_coefficients(bs_deltas, corrections_per_phi_d1)` fits (a, b, c)
via ordinary least squares from vectors of historical BS deltas and the
corresponding per-φ(d₁) corrections observed in the data:

    correction_per_phi_i = (δ_MV_actual_i - δ_BS_i) / (φ(d₁_i) · exp(-q·T_i))

Requires numpy (already present in the project environment).
"""

from __future__ import annotations

import math
from typing import List, Tuple

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_calculation_method import (
    DeltaCalculationMethod,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_result import (
    DeltaResult,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.option_market_state import (
    OptionMarketState,
)


def fit_quadratic_coefficients(
    bs_deltas: List[float],
    corrections_per_phi_d1: List[float],
) -> Tuple[float, float, float]:
    """Fit Hull-White MV quadratic coefficients via ordinary least squares.

    Parameters
    ----------
    bs_deltas:
        Historical BS delta values δ_BS (one per observation).
    corrections_per_phi_d1:
        Historical per-φ(d₁) corrections
        (δ_MV_actual - δ_BS) / (φ(d₁) · exp(-q·T)) for each observation.

    Returns
    -------
    (a, b, c) such that  a + b·δ_BS + c·δ_BS²  ≈ correction_per_phi.
    Returns (0.0, 0.0, 0.0) if the fit cannot be completed (< 3 observations
    or degenerate design matrix).
    """
    import numpy as np  # numpy is a project dependency

    n = len(bs_deltas)
    if n < 3 or n != len(corrections_per_phi_d1):
        return 0.0, 0.0, 0.0

    d = np.asarray(bs_deltas, dtype=float)
    y = np.asarray(corrections_per_phi_d1, dtype=float)
    X = np.column_stack([np.ones(n), d, d ** 2])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return float(coeffs[0]), float(coeffs[1]), float(coeffs[2])
    except (np.linalg.LinAlgError, ValueError):
        return 0.0, 0.0, 0.0


class BSMinimumVarianceDelta(DeltaCalculationMethod):
    """Hull & White (2017) minimum-variance delta.

    Parameters
    ----------
    a, b, c:
        Quadratic correction coefficients.  Defaults to zero (plain BS delta).
        Use `BSMinimumVarianceDelta.from_fit(...)` to calibrate from historical data.
    """

    def __init__(self, a: float = 0.0, b: float = 0.0, c: float = 0.0) -> None:
        self._a = float(a)
        self._b = float(b)
        self._c = float(c)

    @property
    def method_name(self) -> str:
        return "bs_minimum_variance"

    def compute_delta(self, state: OptionMarketState) -> DeltaResult:
        d1, _ = self._d1_d2(
            state.spot, state.strike, state.r, state.implied_vol, state.tau, state.q
        )
        if d1 is None:
            return DeltaResult(
                delta=0.5 if state.option_type.lower() == "call" else -0.5,
                method_name=self.method_name,
                diagnostics={"error": "invalid_inputs"},
            )

        exp_qt = math.exp(-state.q * state.tau)
        cdf_d1 = self._norm_cdf(d1)
        pdf_d1 = self._norm_pdf(d1)

        if state.option_type.lower() == "call":
            delta_bs = exp_qt * cdf_d1
        else:
            delta_bs = exp_qt * (cdf_d1 - 1.0)

        # φ(d₁)·exp(-q·T) is the normalised vega weight
        phi_weight = pdf_d1 * exp_qt
        correction = phi_weight * (self._a + self._b * delta_bs + self._c * delta_bs ** 2)
        delta_mv = delta_bs + correction

        return DeltaResult(
            delta=delta_mv,
            method_name=self.method_name,
            diagnostics={
                "delta_bs": delta_bs,
                "correction": correction,
                "phi_weight": phi_weight,
                "a": self._a,
                "b": self._b,
                "c": self._c,
            },
        )

    @classmethod
    def from_fit(
        cls,
        bs_deltas: List[float],
        corrections_per_phi_d1: List[float],
    ) -> "BSMinimumVarianceDelta":
        """Construct a fitted instance from historical calibration data."""
        a, b, c = fit_quadratic_coefficients(bs_deltas, corrections_per_phi_d1)
        return cls(a=a, b=b, c=c)
