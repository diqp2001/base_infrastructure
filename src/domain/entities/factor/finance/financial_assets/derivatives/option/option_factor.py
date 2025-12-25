from __future__ import annotations
import math
from typing import Optional, Union
from datetime import timedelta

from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor



class OptionFactor(DerivativeFactor):
    """Domain factor representing general option-specific characteristics."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,

    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    # ------------------------------------------------------------
    # Black-Scholes utility functions as instance methods
    # ------------------------------------------------------------
    def _norm_cdf(self, x: float) -> float:
        """Cumulative distribution function for the standard normal distribution."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_pdf(self, x: float) -> float:
        """Probability density function of the standard normal distribution."""
        return (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)

    def _d1_d2(self, S: float, K: float, r: float, sigma: float, T: float):
        """Compute d1 and d2 for Black-Scholes."""
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None, None

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return d1, d2