"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/etf_share_option/etf_share_option_scenario_payoff_factor.py

The dispersion strategy's payoff at maturity in transparent scenarios, per ETF option sold (section 18; European, no
early exercise or dividends: research only). See ETFShareOptionFactor.scenarios:

    market_<move>       every constituent moves by the same amount
    dispersion_<move>   the same average move, the heavier half of the ETF weight +10 % and the rest the opposite
    move: down10, down5, flat, up5, up10

Name: scenario_<scenario>_<measure>, e.g. scenario_dispersion_up5_pnl, measure one of
    pnl          combined + the strategy's net premium ($)
    combined     long basket + short ETF payoff ($)
    long_basket  the constituent options' payoff ($)
    short_etf    what the short ETF option pays (negative, $)
    etf_price    the ETF price in the scenario
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_dispersion_factor import (
    ETFShareOptionDispersionFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    ETFShareOptionFactor, Leg, SCENARIO_MOVES,
)

SCENARIOS = tuple(ETFShareOptionFactor.scenario_name(kind, m) for m in SCENARIO_MOVES for kind in ("market", "dispersion"))
SCENARIO_MEASURES = ("pnl", "combined", "long_basket", "short_etf", "etf_price")


class ETFShareOptionScenarioPayoffFactor(ETFShareOptionDispersionFactor):
    """The dispersion strategy's payoff in one scenario (see the module docstring)."""

    KIND = "scenario"
    MEASURES = tuple(f"{s}_{m}" for s in SCENARIOS for m in SCENARIO_MEASURES)

    def __init__(self, name: str = "scenario_dispersion_flat_pnl", **kwargs):
        super().__init__(name=name, **kwargs)

    def measures(self, etf: Leg, constituents: List[Leg]) -> Dict[str, Optional[float]]:
        if not etf.bid or etf.bid <= 0 or any(not c.ask or c.ask <= 0 for c in constituents):
            return {}
        sizing = self.replicate(etf, constituents)
        net = self.premium(etf, constituents, sizing).net_premium
        return {f"{row['key']}_{m}": row[m] for row in self.scenarios(etf, constituents, sizing, net)
                for m in SCENARIO_MEASURES}
