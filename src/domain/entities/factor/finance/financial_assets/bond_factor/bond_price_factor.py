from __future__ import annotations
from typing import Optional
import math
from .bond_factor import BondFactor


class BondPriceFactor(BondFactor):
    """Price factor for a bond."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Bond Price",
            group="Bond Factor",
            subgroup="Price",
            data_type="float",
            source="model",
            definition="Price of the bond.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_price(self, face_value: float, coupon: float, yield_rate: float, term: float) -> Optional[float]:
        """Calculate bond price from coupon, yield, and term."""
        if yield_rate <= 0 or term <= 0:
            return None

        # Price = PV of coupons + PV of face value
        pv_coupons = sum(coupon / ((1 + yield_rate) ** t) for t in range(1, int(term) + 1))
        pv_face = face_value / ((1 + yield_rate) ** term)
        return pv_coupons + pv_face














