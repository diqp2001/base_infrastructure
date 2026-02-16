from __future__ import annotations
from typing import Optional
import math

from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor


class AnnualizedPriceReturnFactor(FutureFactor):
    """Annualized price return factor."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Annualized Price Return",
            group="Price Factor",
            subgroup="Return",
            data_type="float",
            source="model",
            definition="Annualized return computed from two price observations.",
            factor_id=factor_id,
            **kwargs
        )

    def calculate_annualized_return(
        self,
        start_price: float,
        end_price: float,
        T: float,
        method: str = "geometric"
    ) -> Optional[float]:
        """
        Calculate annualized return.

        Parameters
        ----------
        start_price : float
            Initial price
        end_price : float
            Final price
        T : float
            Time in years
        method : str
            'geometric' (default) or 'simple'

        Returns
        -------
        float | None
        """

        if start_price <= 0 or end_price <= 0 or T <= 0:
            return None

        if method == "geometric":
            # (P_end / P_start)^(1/T) - 1
            return (end_price / start_price) ** (1 / T) - 1

        elif method == "simple":
            # ((P_end / P_start) - 1) / T
            return (end_price / start_price - 1) / T

        else:
            raise ValueError("Method must be 'geometric' or 'simple'")
