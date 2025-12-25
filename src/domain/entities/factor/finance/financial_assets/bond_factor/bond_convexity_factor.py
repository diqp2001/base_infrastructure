from typing import Optional
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondConvexityFactor(BondFactor):
    """Convexity factor for a bond."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Bond Convexity",
            group="Bond Factor",
            subgroup="Convexity",
            data_type="float",
            source="model",
            definition="Measure of bond price curvature relative to interest rate changes.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_convexity(self, price: float, cash_flows: list, yield_rate: float) -> Optional[float]:
        """Calculate bond convexity."""
        if price <= 0 or yield_rate <= 0 or not cash_flows:
            return None

        convexity_sum = sum(t * (t + 1) * cf / ((1 + yield_rate) ** (t + 2)) for t, cf in enumerate(cash_flows, start=1))
        return convexity_sum / price