"""
WW-NTBN: Whalley-Wilmott Prior + Neural Transaction-Band Network
================================================================

Inference wrapper for the WW-NTBN model described in:
  Arzel, M. & Lehdili, N. (2026). "Optimal Delta-Hedging via Structural Prior
  Neural Networks." arXiv:2603.29994.

Architecture (inference-only):
  - 5 hidden layers, 32 units each, ReLU activations
  - 2 output units: [lower_residual, upper_residual] corrections over the
    Whalley-Wilmott closed-form band
  - Outputs are softclamped to ± ww_prior to prevent degenerate bands
  - Input features: [log(spot), log(strike/spot), tau, vol, prev_hedge, r]

When no pre-trained weights are loaded, the policy returns the plain
Whalley-Wilmott band (model_used = 'ww_ntbn_fallback_ww') and logs a
warning rather than raising.

Weights file format: NumPy .npz archive with arrays W0, b0, W1, b1, …
  Wk: (out_dim, in_dim) float64 weight matrix for layer k
  bk: (out_dim,)        float64 bias vector for layer k
"""

import logging
import math
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ['softclamp', 'WWNTBNHedgePolicy']


def softclamp(x: float, lower: float, upper: float, beta: float = 10.0) -> float:
    """Differentiable clamp via scaled sigmoid.

    Approaches `lower` as x → -∞ and `upper` as x → +∞.
    The sharpness of the transition is controlled by `beta`:
    higher beta ≈ harder clamp.

    Args:
        x: Value to clamp.
        lower: Lower bound (must be < upper).
        upper: Upper bound.
        beta: Sharpness parameter (> 0).

    Returns:
        Softclamped value in the open interval (lower, upper).
    """
    if upper <= lower:
        return (lower + upper) / 2.0
    mid = (lower + upper) / 2.0
    half_range = (upper - lower) / 2.0
    t = beta * (x - mid) / half_range
    # Clamp t to avoid overflow in exp for very large beta or x
    t = max(-50.0, min(50.0, t))
    return lower + (upper - lower) / (1.0 + math.exp(-t))


class WWNTBNHedgePolicy:
    """WW-NTBN inference wrapper (Arzel & Lehdili 2026, arXiv:2603.29994).

    Computes a no-trade band half-width as:
        H = max(ww_prior + mean(softclamp(residuals, -ww_prior, ww_prior)), 0)

    where ww_prior is the Whalley-Wilmott closed-form band and residuals are
    the network's two output units.

    When weights are not loaded, H = ww_prior (pure WW fallback).
    """

    INPUT_DIM = 6
    HIDDEN_DIM = 32
    HIDDEN_LAYERS = 5
    OUTPUT_DIM = 2
    SOFTCLAMP_BETA = 10.0

    def __init__(self, weights_path: Optional[str] = None):
        self._W: list = []
        self._b: list = []
        self._loaded: bool = False
        if weights_path is not None:
            self._load_weights(weights_path)

    def _load_weights(self, path: str) -> None:
        """Load weight matrices and bias vectors from a NumPy .npz archive."""
        try:
            data = np.load(path, allow_pickle=False)
            W, b = [], []
            layer = 0
            while f'W{layer}' in data:
                W.append(data[f'W{layer}'].astype(np.float64))
                b.append(data[f'b{layer}'].astype(np.float64))
                layer += 1
            if layer == 0:
                raise ValueError("No weight arrays (W0, b0, …) found in archive.")
            self._W = W
            self._b = b
            self._loaded = True
            logger.info(f"WWNTBNHedgePolicy: loaded {layer}-layer network from {path}")
        except Exception as exc:
            logger.warning(
                f"WWNTBNHedgePolicy: could not load weights from {path!r}: {exc}. "
                "Falling back to Whalley-Wilmott closed-form band."
            )

    def _forward(self, x: np.ndarray) -> np.ndarray:
        """5-layer MLP forward pass with ReLU hidden activations."""
        h = x.copy()
        for i, (W, b) in enumerate(zip(self._W, self._b)):
            h = W @ h + b
            if i < len(self._W) - 1:
                np.maximum(h, 0.0, out=h)  # ReLU in-place
        return h

    def compute_hedge(
        self,
        gamma_net: float,
        spot: float,
        strike: float,
        tau: float,
        vol: float,
        prev_hedge: float,
        r: float,
        cost_rate: float,
        risk_aversion: float,
    ) -> Dict[str, Any]:
        """Compute no-trade band half-width using WW prior + learned residual.

        Args:
            gamma_net: Net portfolio gamma (NETTED across spread legs).
            spot: Underlying spot price S (> 0).
            strike: Reference strike (e.g. long-leg strike) for moneyness feature.
            tau: Time to expiry in years.
            vol: Implied volatility σ (annualised).
            prev_hedge: Current hedge position delta (for state feature).
            r: Risk-free rate (continuously compounded).
            cost_rate: Proportional transaction cost fraction k.
            risk_aversion: CARA risk-aversion coefficient a.

        Returns:
            Dict with:
                half_width (float): Recommended no-trade band half-width.
                model_used (str): 'ww_ntbn' or 'ww_ntbn_fallback_ww'.
                ww_prior (float): Whalley-Wilmott closed-form component.
                residual (float): Mean residual correction applied.
        """
        from .rebalancing_bands import whalley_wilmott_band

        ww_prior = whalley_wilmott_band(
            gamma=gamma_net,
            spot=spot,
            cost_rate=cost_rate,
            risk_aversion=risk_aversion,
            time_to_expiry=tau,
            risk_free_rate=r,
        )

        if not self._loaded:
            return {
                'half_width': ww_prior,
                'model_used': 'ww_ntbn_fallback_ww',
                'ww_prior': ww_prior,
                'residual': 0.0,
            }

        safe_spot = max(spot, 1e-8)
        safe_strike = max(strike, 1e-8)
        x = np.array([
            math.log(safe_spot),
            math.log(safe_strike / safe_spot),
            tau,
            vol,
            prev_hedge,
            r,
        ], dtype=np.float64)

        raw_out = self._forward(x)

        lower_res = softclamp(float(raw_out[0]), -ww_prior, ww_prior, self.SOFTCLAMP_BETA)
        upper_res = softclamp(float(raw_out[1]), -ww_prior, ww_prior, self.SOFTCLAMP_BETA)
        mean_res = (lower_res + upper_res) / 2.0
        half_width = max(ww_prior + mean_res, 0.0)

        return {
            'half_width': half_width,
            'model_used': 'ww_ntbn',
            'ww_prior': ww_prior,
            'residual': mean_res,
        }
