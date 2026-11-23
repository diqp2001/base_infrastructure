"""
ETF call dispersion -> TargetPortfolio (refactor phase P7).

    StrategySignals (ETFCallDispersionTradingStrategy: constituent scores)
      + the ATM call legs (market inputs: premiums bid / ask, deltas, ETF weights on each constituent leg)
      -> select_constituents (names expected to decline excluded)            [model_selection]
      -> DispersionPortfolioConstructionService.construct (N fixed from the full basket, replication, premiums)
      -> TargetPortfolio: the ETF call short N contracts, the selected constituent calls long q_i contracts

Nothing is rewritten: the selection and sizing are the dispersion screener's. This module only expresses their
result as the architecture's boundary object. Positions are sized in contracts (``target_quantity``); their
``target_weight`` is the leg's signed cash premium as a fraction of the ETF calls' premium (information: the
rebalancer sizes quantity targets in units). The legs' net dollar delta is in ``context``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Mapping, Optional, Sequence

from src.application.services.dispersion.dispersion_portfolio_construction_service import (
    WHOLE,
    ConstructedTrade,
    DispersionPortfolioConstructionService,
)
from src.application.services.dispersion.model_selection import ModelFilterConfig, select_constituents
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (  # noqa: E501
    Leg,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio, TargetPortfolioPosition

ORIGINAL, MODEL_FILTERED = "original", "model_filtered"


def construct_dispersion_trade(signals: StrategySignals, etf: Leg, constituents: Sequence[Leg], opened: date,
                               expiry: date, config: Optional[ModelFilterConfig] = None,
                               contracts: str = WHOLE, unscored: Optional[Mapping[str, str]] = None,
                               constructor: Optional[DispersionPortfolioConstructionService] = None
                               ) -> ConstructedTrade:
    """Steps 1-5: selection on the strategy's scores, then the existing dispersion construction.
    ``unscored``: why a constituent has no score (reported with the rejections); ``constructor``: the caller's
    DispersionPortfolioConstructionService (else one with ``contracts``)."""
    selection = select_constituents([c.symbol for c in constituents], dict(signals.values),
                                    config or ModelFilterConfig(), unscored)
    constructor = constructor or DispersionPortfolioConstructionService(contracts)
    return constructor.construct(opened, expiry, etf, constituents, selection)


def dispersion_target_portfolio(trade: ConstructedTrade, as_of: Optional[datetime] = None,
                                strategy: str = MODEL_FILTERED, strategy_name: str = "etf_call_dispersion",
                                option_symbol: Optional[Callable[[str, date, float], str]] = None
                                ) -> TargetPortfolio:
    """Steps 6-8: the trade's legs (strategy 'original' = full basket, 'model_filtered' = selected) as a
    TargetPortfolio of option contracts. ``option_symbol`` names a leg's contract (default: the cycle's OCC symbol)."""
    if option_symbol is None:                     # imported here: the dispersion trading cycle imports this module
        from src.application.services.dispersion.dispersion_trading_cycle import occ_symbol as option_symbol
    if strategy not in (ORIGINAL, MODEL_FILTERED):
        raise ValueError(f"strategy must be '{ORIGINAL}' or '{MODEL_FILTERED}'")
    legs = trade.original if strategy == ORIGINAL else trade.filtered
    by_symbol = {c.symbol: c for c in trade.constituents}
    short_premium = legs.short_premium
    positions = [TargetPortfolioPosition(
        symbol=option_symbol(trade.etf.symbol, trade.expiry, trade.etf.strike), asset_type="ETFShareOption",
        target_quantity=-float(legs.etf_contracts), target_weight=-1.0)]
    for underlying, qty in legs.positions.items():
        leg = by_symbol[underlying]
        premium = qty * leg.multiplier * leg.ask
        positions.append(TargetPortfolioPosition(
            symbol=option_symbol(underlying, trade.expiry, leg.strike), asset_type="CompanyShareOption",
            target_quantity=float(qty), target_weight=premium / short_premium if short_premium else 0.0))
    deltas = [trade.etf.dollar_delta(-legs.etf_contracts)] + [
        by_symbol[s].dollar_delta(q) for s, q in legs.positions.items()]
    net_delta = None if any(d is None for d in deltas) else sum(deltas)
    return TargetPortfolio(as_of=as_of, positions=tuple(positions), strategy_name=strategy_name,
                           construction=f"etf_call_dispersion:{strategy}",
                           context={"etf_contracts": legs.etf_contracts, "short_premium": legs.short_premium,
                                    "long_premium": legs.long_premium,
                                    "net_initial_premium": legs.net_initial_premium,
                                    "net_dollar_delta": net_delta,
                                    "rejected": dict(trade.selection.rejected)})
