"""
Backtest fills with costs (P.08.04). A backtest order used to be booked at the decision price with no commission;
live market orders pay the ask (buy) or receive the bid (sell) and IBKR's commission.

    CommissionModel        IBKR-style commission per order: per share, a minimum, a cap as a share of trade value
    BidAskFillModel        buy at the ask, sell at the bid of the decision bar + commission; no usable quote ->
                           no fill (the order is refused, as the live gate refuses an order it cannot price)
    StoredBidAskQuotes     bid / ask = the closes of the stored IBKR BID / ASK bars, read through the history
                           frontier (only bars closed at the decision time)

TradeManager.fill_model (backtest only) applies it; live fills come from the broker's executions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class Fill:
    price: Optional[float]                  # None = no fill
    commission: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class CommissionModel:
    per_share: float
    minimum: float
    max_pct_of_value: float                 # IBKR: never more than this share of the trade value

    @classmethod
    def from_config(cls, cfg: dict) -> "CommissionModel":
        return cls(per_share=float(cfg["per_share"]), minimum=float(cfg["minimum"]),
                   max_pct_of_value=float(cfg["max_pct_of_value"]))

    def __call__(self, quantity: float, price: float) -> float:
        commission = max(self.minimum, self.per_share * abs(quantity))
        return round(min(commission, self.max_pct_of_value * abs(quantity) * price), 2)


QuoteSource = Callable[[str, datetime], Optional[Tuple[float, float]]]


class BidAskFillModel:

    def __init__(self, quotes: QuoteSource, commission: CommissionModel):
        self.quotes = quotes
        self.commission = commission
        # what the costs did over a run: fills, trades refused for want of a quote, commissions, and the spread paid
        # against the decision price (|fill - decision| x quantity)
        self.fills = self.refused = 0
        self.commission_total = self.spread_cost_total = 0.0

    @classmethod
    def from_config(cls, cfg: dict, quotes: QuoteSource) -> "BidAskFillModel":
        """cfg = project config 'execution_costs': {'fill': 'bid_ask', 'commission': {...}}."""
        if cfg.get("fill") != "bid_ask":
            raise ValueError(f"execution_costs.fill must be 'bid_ask', got {cfg.get('fill')!r}")
        return cls(quotes, CommissionModel.from_config(cfg["commission"]))

    def __call__(self, ticker: str, quantity: float, decision_price: float, when: datetime) -> Fill:
        quote = self.quotes(ticker, when)
        if quote is None:
            self.refused += 1
            return Fill(None, reason=f"no bid / ask for {ticker} at {when}")
        bid, ask = quote
        if not (bid > 0 and ask >= bid):
            self.refused += 1
            return Fill(None, reason=f"invalid quote for {ticker} at {when}: bid {bid}, ask {ask}")
        price = ask if quantity > 0 else bid
        fill = Fill(price, self.commission(quantity, price))
        self.fills += 1
        self.commission_total += fill.commission
        self.spread_cost_total += abs(price - decision_price) * abs(quantity)
        return fill

    def summary(self) -> dict:
        return {"fills": self.fills, "refused": self.refused, "commission": round(self.commission_total, 2),
                "spread_cost_vs_decision_price": round(self.spread_cost_total, 2)}


class StoredBidAskQuotes:
    """(bid, ask) of `ticker` at `when` from the stored BID / ASK bar closes of the newest bar closed at `when`
    (the history frontier hides open bars); None when either side is missing or older than `max_age`."""

    def __init__(self, history_service, ticker_to_entity: Dict[str, int], frequency: str, bar_minutes: int,
                 max_age: timedelta, factor_type: str = "company_share_factor"):
        self.history_service = history_service
        self.ticker_to_entity = dict(ticker_to_entity)
        self.frequency = frequency
        self.bar_minutes = int(bar_minutes)
        self.max_age = max_age
        self.factor_type = factor_type
        self._cached_at: Optional[datetime] = None
        self._cache: Dict[str, Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp], float, float]] = {}

    def _load(self, when: datetime) -> None:
        """Both sides for every ticker at once (one query per side and decision time)."""
        entities = {eid: t for t, eid in self.ticker_to_entity.items()}
        start = pd.Timestamp(when) - self.max_age - timedelta(minutes=self.bar_minutes)
        newest = {}
        for side in ("BID", "ASK"):
            panel = self.history_service.get_factor_value_panel(
                entities, factor_name="close", factor_type=self.factor_type, frequency=self.frequency,
                subgroup=side, start=start.to_pydatetime())
            for ticker in getattr(panel, "columns", []):
                series = panel[ticker].dropna()
                newest[(ticker, side)] = (series.index[-1], float(series.iloc[-1])) if len(series) else None
        self._cache = {}
        for ticker in self.ticker_to_entity:
            bid, ask = newest.get((ticker, "BID")), newest.get((ticker, "ASK"))
            if bid is not None and ask is not None:
                self._cache[ticker] = (bid[0], ask[0], bid[1], ask[1])
        self._cached_at = when

    def __call__(self, ticker: str, when: datetime) -> Optional[Tuple[float, float]]:
        if self._cached_at != when:
            self._load(when)
        found = self._cache.get(ticker)
        if found is None:
            return None
        bid_bar, ask_bar, bid, ask = found
        # bars are keyed by their START: the bar closed at `when` starts one bar earlier; max_age allows older ones
        oldest_start = pd.Timestamp(when) - self.max_age - timedelta(minutes=self.bar_minutes)
        if min(bid_bar, ask_bar) < oldest_start:
            return None
        return bid, ask
