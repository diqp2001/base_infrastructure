"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/etf_share_option/etf_share_option_reverse_premium_factor.py

The dispersion strategy reversed, per ETF option bought (information, owner 2026-11-06): the ETF option bought at its
ask, the replicating constituent options sold at their bids.

    reverse_premium_net                    constituent proceeds - ETF option cost ($)
    reverse_premium_net_pct                net / ETF option cost
    reverse_premium_etf_option_cost        the ETF option's ask x multiplier
    reverse_premium_constituent_proceeds   sum_i contracts_i x multiplier_i x bid_i
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_dispersion_factor import (
    ETFShareOptionDispersionFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import Leg


class ETFShareOptionReversePremiumFactor(ETFShareOptionDispersionFactor):
    """The reversed dispersion strategy's net premium (see the module docstring)."""

    KIND = "reverse_premium"
    MEASURES = ("net", "net_pct", "etf_option_cost", "constituent_proceeds")

    def __init__(self, name: str = "reverse_premium_net", **kwargs):
        super().__init__(name=name, **kwargs)

    def measures(self, etf: Leg, constituents: List[Leg]) -> Dict[str, Optional[float]]:
        r = self.reverse_premium(etf, constituents, self.replicate(etf, constituents))
        if r is None:
            return {}
        return {"net": r.net_premium, "net_pct": r.net_premium_pct, "etf_option_cost": r.etf_call_cost,
                "constituent_proceeds": r.constituent_proceeds}
