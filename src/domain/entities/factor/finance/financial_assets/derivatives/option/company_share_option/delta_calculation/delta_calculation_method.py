"""Abstract base class for pluggable delta-calculation methods.

All concrete implementations must override `compute_delta` and `method_name`.
Shared Black-Scholes helpers (_d1_d2, _norm_cdf, _norm_pdf, _bs_delta) are
provided here so subclasses do not duplicate formula code.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_result import (
    DeltaResult,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.option_market_state import (
    OptionMarketState,
)


class DeltaCalculationMethod(ABC):
    """Interface for a single pluggable delta-hedging strategy."""

    @abstractmethod
    def compute_delta(self, state: OptionMarketState) -> DeltaResult:
        """Compute the target hedge delta from the current market snapshot."""

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Stable string identifier for this method (used in DeltaResult)."""

    # ------------------------------------------------------------------ #
    # Shared Black-Scholes helpers                                         #
    # ------------------------------------------------------------------ #

    def _d1_d2(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        q: float = 0.0,
    ) -> Tuple[Optional[float], Optional[float]]:
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None, None
        try:
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            return d1, d1 - sigma * math.sqrt(T)
        except (ValueError, ZeroDivisionError):
            return None, None

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_pdf(self, x: float) -> float:
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    def _bs_delta(self, state: OptionMarketState) -> float:
        """Black-Scholes-Merton delta including dividend yield."""
        d1, _ = self._d1_d2(
            state.spot, state.strike, state.r, state.implied_vol, state.tau, state.q
        )
        if d1 is None:
            return 0.5 if state.option_type.lower() == "call" else -0.5
        exp_qt = math.exp(-state.q * state.tau)
        cdf_d1 = self._norm_cdf(d1)
        if state.option_type.lower() == "call":
            return exp_qt * cdf_d1
        return exp_qt * (cdf_d1 - 1.0)

    def _bs_price(self, state: OptionMarketState) -> float:
        """Black-Scholes-Merton option price."""
        d1, d2 = self._d1_d2(
            state.spot, state.strike, state.r, state.implied_vol, state.tau, state.q
        )
        if d1 is None or d2 is None:
            return 0.0
        exp_qt = math.exp(-state.q * state.tau)
        exp_rt = math.exp(-state.r * state.tau)
        if state.option_type.lower() == "call":
            return (
                state.spot * exp_qt * self._norm_cdf(d1)
                - state.strike * exp_rt * self._norm_cdf(d2)
            )
        return (
            state.strike * exp_rt * self._norm_cdf(-d2)
            - state.spot * exp_qt * self._norm_cdf(-d1)
        )
