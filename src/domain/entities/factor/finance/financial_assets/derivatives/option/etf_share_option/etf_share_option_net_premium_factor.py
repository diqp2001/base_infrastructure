"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/etf_share_option/etf_share_option_net_premium_factor.py

The dispersion strategy's cost on the broker's prices, per ETF option sold (owner, 2026-11-06): the ETF option sold
at its bid, the constituent options that replicate its holdings bought at their asks.

    premium_net               ETF proceeds - constituent cost ($; >= 0: an opportunity)
    premium_net_pct           net / ETF proceeds
    premium_short_proceeds    the ETF option's bid x multiplier
    premium_long_cost         sum_i contracts_i x multiplier_i x ask_i
    premium_mid_net           the net premium at mids (information)
    premium_transaction_cost  what the bid / ask costs against mids (information)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_dispersion_factor import (
    ETFShareOptionDispersionFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import Leg


class ETFShareOptionNetPremiumFactor(ETFShareOptionDispersionFactor):
    """The dispersion strategy's net premium (see the module docstring)."""

    KIND = "premium"
    MEASURES = ("net", "net_pct", "short_proceeds", "long_cost", "mid_net", "transaction_cost")

    def __init__(self, name: str = "premium_net", **kwargs):
        super().__init__(name=name, **kwargs)

    def measures(self, etf: Leg, constituents: List[Leg]) -> Dict[str, Optional[float]]:
        if not etf.bid or etf.bid <= 0 or any(not c.ask or c.ask <= 0 for c in constituents):
            return {}
        p = self.premium(etf, constituents, self.replicate(etf, constituents))
        return {"net": p.net_premium, "net_pct": p.net_premium_pct, "short_proceeds": p.short_proceeds,
                "long_cost": p.long_cost, "mid_net": p.mid_net_premium, "transaction_cost": p.transaction_cost}
