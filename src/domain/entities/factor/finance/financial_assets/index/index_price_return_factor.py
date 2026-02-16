from __future__ import annotations
from typing import Optional
import math

from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor


class IndexPriceReturnFactor(IndexFactor):
    """Annualized price return factor."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Price Return",
            group="Return Factor",
            subgroup="Return",
            data_type="float",
            source="model",
            definition="Return computed from two price observations.",
            factor_id=factor_id,
            **kwargs
        )

    def calculate(
        self,
        start_price: float,
        end_price: float,
        method: str = "geometric"
    ) -> Optional[float]:
        """
        Calculate return between two price observations.

        Parameters
        ----------
        start_price : float
            Initial price
        end_price : float
            Final price
        method : str
            'geometric' (default) or 'simple'

        Returns
        -------
        float | None
        """

        if start_price <= 0 or end_price <= 0:
            return None

        if method == "geometric":
            # (P_end / P_start) - 1
            return (end_price / start_price) - 1

        elif method == "simple":
            # Same formula in a two-point case
            return (end_price - start_price) / start_price

        else:
            raise ValueError("Method must be 'geometric' or 'simple'")

