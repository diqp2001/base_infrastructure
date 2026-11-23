"""
SPXCallSpreadTradingStrategy — the SPX / SPY call market maker's entry rule as a TradingStrategy.

    configured option (the universe's CompanyShareOption) -> StrategySignals {option: entry weight (short by default)}
      -> entry_target: TargetPortfolio (the option at its entry weight), sent only while the book is flat in it
         (``wants_entry``: open once, never resized while held)
    book greeks (actual holdings) -> delta-hedge overlay (construction/delta_hedge.py, band from the project's hedging
      model) -> hedge TargetPortfolio (the hedge symbol at -book delta)

Neither leg ranks a universe: the entry is a fixed weight on one contract and the hedge is position management on
what the account holds. The strategy holds their parameters (option, entry weight, hedge symbol); the hedging band
models (Whalley-Wilmott, Zakamouline, WW-NTBN) stay in the project.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy
from src.domain.entities.finance.portfolio.construction.delta_hedge import hedge_target_portfolio
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio

OPTION_TYPE = "CompanyShareOption"
HEDGE_TYPE = "CompanyShare"


class SPXCallSpreadTradingStrategy(TradingStrategy):

    def __init__(self, name: str = "spx_call_spread", option_symbol: Optional[str] = None,
                 entry_weight: float = -0.2, hedge_symbol: str = "SPY", frequency: Optional[str] = None, **kwargs):
        if not math.isfinite(entry_weight):
            raise ValueError("the entry weight must be finite")
        super().__init__(name=name, frequency=frequency, **kwargs)
        self.option_symbol = option_symbol
        self.entry_weight = float(entry_weight)
        self.hedge_symbol = hedge_symbol

    @property
    def calculate_dependencies(self) -> list:
        """No ranking factor: the entry is a fixed weight on the configured option."""
        return []

    def evaluate(self, dependencies: Dict[str, Any] = None, as_of: Optional[datetime] = None) -> StrategySignals:
        values = {self.option_symbol: self.entry_weight} if self.option_symbol else {}
        return StrategySignals(as_of=as_of, values=values, asset_type=OPTION_TYPE)

    def wants_entry(self, current_quantity: float) -> bool:
        """Open the option only while the book holds none of it (an open position is never resized)."""
        return bool(self.option_symbol) and current_quantity == 0

    def entry_target(self, as_of: Optional[datetime] = None) -> TargetPortfolio:
        """The option at its entry weight (weight = signal: no ranking, no scaling)."""
        signals = self.evaluate(as_of=as_of)
        return TargetPortfolio.from_weights(dict(signals.values), as_of=as_of, asset_type=OPTION_TYPE,
                                            strategy_name=self.name, construction="option_entry")

    def hedge_target(self, quantity: float, as_of: Optional[datetime] = None) -> TargetPortfolio:
        """The hedge symbol held at ``quantity`` shares (the delta-hedge overlay's target)."""
        if not math.isfinite(quantity):
            raise ValueError(f"hedge size is not finite ({quantity})")
        return hedge_target_portfolio(self.hedge_symbol, quantity, as_of=as_of, asset_type=HEDGE_TYPE,
                                      strategy_name=self.name)
