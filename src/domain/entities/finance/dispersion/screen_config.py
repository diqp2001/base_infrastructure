"""Settings of the dispersion screen. Defaults are the specification's; a project's config.py overrides them,
business logic only reads them from here (never literal values)."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class DispersionScreenConfig:
    # universe / holdings
    max_constituents: int = 49
    min_constituents: int = 2
    max_holdings_age_days: int = 7            # holdings older than this at the screening date: rejected
    min_equity_weight: float = 0.90           # equity lines must be >= 90 % of the fund before normalising
    weight_sum_tolerance: float = 0.02        # |sum of every line's weight - 100 %| allowed (incomplete file)
    leveraged_name_markers: Tuple[str, ...] = field(default_factory=lambda: (
        "2X", "3X", "ULTRA", "LEVERAGED", "INVERSE", "BEAR", "SHORT ", "-1X", "-2X", "-3X"))
    # options (P.03 – P.06)
    target_dte: int = 30
    min_dte: int = 20
    max_dte: int = 60
    min_option_coverage: float = 0.95
    max_etf_option_spread: float = 0.05
    max_stock_option_spread: float = 0.10
    delta_tolerance: float = 0.01
    require_same_expiration: bool = True
    max_quote_age_seconds: float = 60.0
