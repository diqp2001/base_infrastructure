from datetime import date
from typing import Optional

from src.domain.entities.finance.financial_assets.share.share import Share


class ETFShare(Share):
    """
    Exchange-traded fund share: trades like a share, holds a basket. Identification only; the basket itself is a
    point-in-time Universe (UniverseConstituent rows with weight, start_date, end_date), prices are factors.

    leverage_factor: 1 for a plain fund, 2 / 3 for leveraged, negative for inverse funds.
    replication: "physical" (holds the securities), "sampling", or "synthetic" (swaps / derivatives).
    """

    def __init__(
        self,
        id: Optional[int],
        symbol: str,
        currency_id: int,
        exchange_id: int,
        name: Optional[str] = None,
        issuer: Optional[str] = None,
        asset_class: Optional[str] = None,
        leverage_factor: float = 1.0,
        replication: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        super().__init__(id=id, name=name, symbol=symbol, start_date=start_date, end_date=end_date)
        self.currency_id = currency_id
        self.exchange_id = exchange_id
        self.issuer = issuer
        self.asset_class = asset_class
        self.leverage_factor = leverage_factor
        self.replication = replication

    @property
    def is_leveraged(self) -> bool:
        return abs(self.leverage_factor or 1.0) > 1.0

    @property
    def is_inverse(self) -> bool:
        return (self.leverage_factor or 1.0) < 0.0

    @property
    def is_synthetic(self) -> bool:
        return (self.replication or "").lower() == "synthetic"
