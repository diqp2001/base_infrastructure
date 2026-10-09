"""
SPXCallSpreadTradingCycle — everything the SPX market maker does at one bar.

Same role as STMTradingCycle in the Spatio-Temporal Momentum projects: the
Misbuffet algorithm (backtest) or a live loop calls ``step(time, data, portfolio)``
once per bar and the cycle decides; the caller only supplies the bar and a
portfolio gateway.  The steps are those of the original
market_making_SPX_call_spread_project Algorithm.on_data, in the same order:

1. factor refresh at ``time`` through the MarketDataHistoryService frontier
   (FactorUpdater; was ModelTrainer.train_complete_pipeline);
2. entry: when the book holds none of the universe's first CompanyShareOption,
   target ``option_entry_weight`` of it (short by default);
3. position book: open option positions + greeks resolved at ``time``;
4. Strategy.manage_existing_positions -> exits and the aggregate delta-hedge decision;
5. hedge: when the band is breached, target ``target_hedge_delta`` shares of the
   hedge symbol (SPY).

``portfolio`` is any object with ``quantity(ticker) -> int`` and
``set_holdings(targets, data)``; in the engine it wraps UnifiedPortfolioManager.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


@dataclass
class CycleResult:
    time: datetime
    factors_updated: bool = False
    option_order: Optional[Dict[Any, Any]] = None      # targets sent for the option entry
    hedge_order: Optional[Dict[Any, Any]] = None       # targets sent for the delta hedge
    positions: int = 0                                  # open option positions after the entry
    portfolio_delta: Optional[float] = None
    portfolio_gamma: Optional[float] = None
    portfolio_hedge: Dict[str, Any] = field(default_factory=dict)
    exited_position_ids: List[str] = field(default_factory=list)
    hedge_spot: Optional[float] = None
    note: str = ""
    error: Optional[str] = None

    @property
    def traded(self) -> bool:
        return self.option_order is not None or self.hedge_order is not None

    def summary(self) -> Dict[str, Any]:
        """JSON-friendly view (progress.json / results.json)."""
        return {
            'time': str(self.time),
            'factors_updated': self.factors_updated,
            'option_order': _jsonable(self.option_order),
            'hedge_order': _jsonable(self.hedge_order),
            'positions': self.positions,
            'portfolio_delta': self.portfolio_delta,
            'portfolio_gamma': self.portfolio_gamma,
            'should_hedge': bool(self.portfolio_hedge.get('should_hedge')),
            'exited_position_ids': list(self.exited_position_ids),
            'hedge_spot': self.hedge_spot,
            'note': self.note,
            'error': self.error,
        }


def _jsonable(targets):
    if targets is None:
        return None
    return {getattr(k, '__name__', str(k)): v for k, v in targets.items()}


def bar_close(data, symbol: str) -> Optional[float]:
    """Close of ``symbol`` in a Misbuffet Slice (Symbol keys) or a plain {symbol: bar} dict."""
    bars = getattr(data, 'bars', None)
    if bars is None and isinstance(data, dict):
        bars = data.get('bars', {})
    for key, bar in (bars or {}).items():
        if str(getattr(key, 'value', key)) == symbol:
            close = getattr(bar, 'close', None)
            return float(close) if close is not None else None
    return None


class SPXCallSpreadTradingCycle:

    def __init__(self, strategy, position_book, factor_updater=None, option_ticker: Optional[str] = None,
                 option_entry_weight: float = -0.2, hedge_symbol: str = 'SPY', log=None):
        self.strategy = strategy
        self.position_book = position_book
        self.factor_updater = factor_updater
        self.option_ticker = option_ticker
        self.option_entry_weight = option_entry_weight
        self.hedge_symbol = hedge_symbol
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log = log or self.logger.info

    def step(self, time: datetime, data, portfolio) -> CycleResult:
        result = CycleResult(time=time)
        # 1. factors at the bar time (frontier-clipped). A failure skips the bar, as the
        #    original skipped trading when the training pipeline returned an error.
        if self.factor_updater is not None:
            try:
                self.factor_updater.update(time)
                result.factors_updated = True
            except Exception as e:
                result.error = f"factor refresh failed: {e}"
                result.note = "bar skipped"
                return result

        # 2. entry: only when the book is flat in the option
        if self.option_ticker and portfolio.quantity(self.option_ticker) == 0:
            targets = {CompanyShareOption: {'name': self.option_ticker, 'weight': self.option_entry_weight}}
            portfolio.set_holdings(targets, data)
            result.option_order = targets
            self.log(f"Option entry {self.option_ticker} weight {self.option_entry_weight} at {time}")

        # 3. book after the entry, with greeks resolved at the bar time
        positions = self.position_book.load_positions(time)
        market_data = self.position_book.market_data(positions, time)
        self.position_book.enrich(positions, market_data)
        result.positions = len(positions)

        # 4. exits + aggregate delta-hedge decision
        mgmt = self.strategy.manage_existing_positions(
            positions=positions, market_data=data, position_market_data=market_data)
        if mgmt.get('error'):
            result.error = f"position management failed: {mgmt['error']}"
            return result
        result.exited_position_ids = list(mgmt.get('exited_position_ids', []))
        hedge = mgmt.get('portfolio_hedge', {}) or {}
        result.portfolio_hedge = hedge
        result.portfolio_delta = hedge.get('portfolio_delta')
        result.portfolio_gamma = hedge.get('portfolio_gamma')

        # 5. delta hedge in the hedge symbol (quantity = target hedge delta)
        if hedge.get('should_hedge') and hedge.get('target_hedge_delta') is not None:
            result.hedge_spot = bar_close(data, self.hedge_symbol)
            target = float(hedge['target_hedge_delta'])
            targets = {CompanyShare: {'name': self.hedge_symbol, 'quantity': target}}
            portfolio.set_holdings(targets, data)
            result.hedge_order = targets
            self.log(f"Delta hedge {hedge.get('hedge_direction', '')}: {self.hedge_symbol} qty {target:.4f} "
                     f"(spot {result.hedge_spot}, book delta {result.portfolio_delta})")
        elif not result.traded:
            result.note = "no trade"
        return result
