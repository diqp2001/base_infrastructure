"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/etf_share_option/etf_share_option_implied_correlation_factor.py

Weighted average implied correlation of the ETF's constituents from its options (owner, 2026-11-06):

    sigma_etf^2 = sum_i w_i^2 sigma_i^2 + rho sum_{i != j} w_i w_j sigma_i sigma_j

    implied_correlation_model     the broker's model volatilities on both sides
    implied_correlation_etf_bid   the ETF volatility implied by its bid, the constituents' by their asks (the strategy)
    implied_correlation_etf_ask   the ETF volatility implied by its ask, the constituents' by their bids (reversed)
    implied_correlation_etf_iv    the ETF option's model volatility (input, information)
    implied_correlation_weighted_iv  sum_i w_i sigma_i of the constituents' model volatilities (input, information)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_dispersion_factor import (
    ETFShareOptionDispersionFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import Leg


class ETFShareOptionImpliedCorrelationFactor(ETFShareOptionDispersionFactor):
    """Implied correlation from the dispersion legs' volatilities (see the module docstring)."""

    KIND = "implied_correlation"
    MEASURES = ("model", "etf_bid", "etf_ask", "etf_iv", "weighted_iv")

    def __init__(self, name: str = "implied_correlation_model", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def fields(self):
        """The leg terms and only the volatilities the measure reads: a missing bid volatility does not block the
        model's correlation."""
        needed = {"etf_bid": ("bid_iv", "ask_iv"), "etf_ask": ("ask_iv", "bid_iv")}.get(self.measure, ("iv",))
        return ("underlying_price", "strike", "multiplier") + needed

    def measures(self, etf: Leg, constituents: List[Leg]) -> Dict[str, Optional[float]]:
        if self.measure == "etf_iv":
            return {"etf_iv": etf.implied_vol}
        if self.measure == "weighted_iv":
            return {"weighted_iv": self.weighted_implied_vol(constituents)}
        if self.measure == "etf_bid":
            return {"etf_bid": self.implied_correlation(etf.bid_implied_vol, constituents, vol="ask_implied_vol")}
        if self.measure == "etf_ask":
            return {"etf_ask": self.implied_correlation(etf.ask_implied_vol, constituents, vol="bid_implied_vol")}
        return {"model": self.implied_correlation(etf.implied_vol, constituents)}
