from typing import Optional
from domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondDurationFactor(BondFactor):
    """Duration factor for a bond (sensitivity to interest rate)."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Bond Duration",
            group="Bond Factor",
            subgroup="Duration",
            data_type="float",
            source="model",
            definition="Macaulay duration of the bond.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_duration(self, price: float, cash_flows: list, yield_rate: float) -> Optional[float]:
        """Calculate Macaulay duration."""
        if price <= 0 or yield_rate <= 0 or not cash_flows:
            return None

        weighted_sum = sum(t * cf / ((1 + yield_rate) ** t) for t, cf in enumerate(cash_flows, start=1))
        return weighted_sum / price