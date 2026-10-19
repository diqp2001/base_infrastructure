from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor


from src.domain.entities.factor.series_dependencies import SeriesPriceReturn


class IndexFuturePriceReturnFactor(SeriesPriceReturn, IndexFutureFactor):
    """Annualized price return factor."""

    def __init__(self, factor_id: Optional[int] = None, name: str = "return_daily", group: str = "return", subgroup: Optional[str] = "daily",
                 frequency: Optional[str] = "1d", data_type: Optional[str] = "numeric",
                 source: Optional[str] = "calculated", **kwargs):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, factor_id=factor_id, **kwargs)

    def price_return(
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


IndexFuturePriceReturnFactor.RAW_FACTOR_TYPE = __import__("src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor", fromlist=["IndexFutureFactor"]).IndexFutureFactor
