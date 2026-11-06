"""
P.06 data quality and liquidity of one option leg (pure): a usable two-sided executable quote, IBKR model greeks,
a live (not frozen / delayed) quote no older than MAX_QUOTE_AGE, and the liquidity minimums (spread, volume, open
interest). Returns the reasons a leg is unusable; empty = usable.
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


def option_quality_problems(option: OptionQuote, now: datetime, config: DispersionScreenConfig) -> List[str]:
    q, g = option.quote, option.greeks
    problems = []
    if not q.two_sided:
        problems.append(f"no two-sided quote (bid {q.bid}, ask {q.ask})")
    if g.delta is None or g.delta <= 0:
        problems.append("no model delta")
    problems += freshness_problems(q, now, config)
    return problems


def option_liquidity_problems(option: OptionQuote, config: DispersionScreenConfig, is_etf: bool) -> List[str]:
    q = option.quote
    max_spread = config.max_etf_option_spread if is_etf else config.max_stock_option_spread
    min_volume = config.min_etf_option_volume if is_etf else config.min_stock_option_volume
    min_oi = config.min_etf_open_interest if is_etf else config.min_stock_open_interest
    problems = []
    if q.spread_pct is not None and q.spread_pct > max_spread:
        problems.append(f"spread {q.spread_pct:.1%} > {max_spread:.0%}")
    if min_volume > 0 and (q.volume or 0) < min_volume:
        problems.append(f"volume {q.volume} < {min_volume:g}")
    if min_oi > 0 and (option.open_interest is None or option.open_interest < min_oi):
        problems.append(f"open interest {option.open_interest} < {min_oi:g}")
    return problems
