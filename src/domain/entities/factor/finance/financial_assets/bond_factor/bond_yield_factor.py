from typing import Optional
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondYieldFactor(BondFactor):
    """Yield factor for a bond."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Bond Yield",
            group="Bond Factor",
            subgroup="Yield",
            data_type="float",
            source="model",
            definition="Yield to maturity of the bond.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_yield(self, price: float, face_value: float, coupon: float, term: float) -> Optional[float]:
        """Simple approximation of yield to maturity (YTM)."""
        if price <= 0 or term <= 0:
            return None
        return (coupon + (face_value - price) / term) / ((face_value + price) / 2)