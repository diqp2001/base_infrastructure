"""
P.06 data quality and liquidity of one option leg (pure). The price the strategy trades at must be quoted (owner,
2026-11-06): the ETF call is sold -> it needs a bid; a constituent call is bought -> it needs an ask. The other side,
the spread and the greeks are information only. Plus a live (not frozen / delayed) quote no older than
MAX_QUOTE_AGE and the optional volume / open interest minimums. Returns the reasons a leg is unusable; empty = usable.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from src.domain.entities.finance.dispersion.option_data import OptionQuote, Quote
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig

LIVE = 1


def freshness_problems(quote: Quote, now: datetime, config: DispersionScreenConfig) -> List[str]:
    problems = []
    if quote.error:
        problems.append(f"quote error {quote.error}")
    if quote.market_data_type not in (None, LIVE) and not config.allow_frozen_quotes:
        kind = {2: "frozen", 3: "delayed", 4: "delayed frozen"}.get(quote.market_data_type, str(quote.market_data_type))
        problems.append(f"{kind} quote (market closed or no live data)")
    if quote.quote_time is None:
        problems.append("no quote time")
    elif (now - quote.quote_time).total_seconds() > config.max_quote_age_seconds:
        problems.append(f"quote {(now - quote.quote_time).total_seconds():.0f}s old "
                        f"(max {config.max_quote_age_seconds:g}s)")
    return problems


SELL, BUY = "sell", "buy"


def option_quality_problems(option: OptionQuote, now: datetime, config: DispersionScreenConfig,
                            side: str) -> List[str]:
    """side: SELL (the ETF call: its bid is the price) or BUY (a constituent call: its ask is the price)."""
    q = option.quote
    problems = []
    if side == SELL and not (q.bid is not None and q.bid > 0):
        problems.append(f"no bid (bid {q.bid})")
    if side == BUY and not (q.ask is not None and q.ask > 0):
        problems.append(f"no ask (ask {q.ask})")
    problems += freshness_problems(q, now, config)
    return problems


def option_liquidity_problems(option: OptionQuote, config: DispersionScreenConfig, is_etf: bool) -> List[str]:
    q = option.quote
    min_volume = config.min_etf_option_volume if is_etf else config.min_stock_option_volume
    min_oi = config.min_etf_open_interest if is_etf else config.min_stock_open_interest
    problems = []
    if min_volume > 0 and (q.volume or 0) < min_volume:
        problems.append(f"volume {q.volume} < {min_volume:g}")
    if min_oi > 0 and (option.open_interest is None or option.open_interest < min_oi):
        problems.append(f"open interest {option.open_interest} < {min_oi:g}")
    return problems
