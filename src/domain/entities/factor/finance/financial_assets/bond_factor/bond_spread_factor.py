from typing import Optional
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondSpreadFactor(BondFactor):
    """Spread factor for a bond (vs benchmark yield)."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Bond Spread",
            group="Bond Factor",
            subgroup="Spread",
            data_type="float",
            source="model",
            definition="Spread of the bond yield over benchmark yield.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_spread(self, bond_yield: float, benchmark_yield: float) -> Optional[float]:
        """Calculate spread in percentage points."""
        if bond_yield is None or benchmark_yield is None:
            return None
        return bond_yield - benchmark_yield