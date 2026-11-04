"""P.08.08: bars validated at import — an inconsistent bar is rejected (never stored) and logged as an anomaly."""

import logging
from decimal import Decimal

import pytest

from src.domain.entities.factor.bar_validation import bar_problems, split_valid_bars
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import (
    IBKRFactorValueRepository,
)

GOOD = {"date": "20261005 09:30:00", "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5, "volume": 1200}


def bar(**changes):
    return {**GOOD, **changes}


def test_a_consistent_bar_is_valid():
    assert bar_problems(GOOD) == []
    assert bar_problems(bar(volume=Decimal("0"))) == []                  # no trade in the window: volume 0 is fine


@pytest.mark.parametrize("changes, expected", [
    ({"close": 0.0}, "price <= 0"),
    ({"low": -1.0}, "price <= 0"),
    ({"low": 102.0}, "low 102 > high 101"),
    ({"open": 101.5}, "open 101.5 outside low 99.5 .. high 101"),
    ({"close": 99.0}, "close 99 outside low 99.5 .. high 101"),
    ({"volume": -5}, "volume -5 < 0"),
    ({"high": "n/a"}, "non-numeric price high"),
    ({"close": float("nan")}, "non-numeric price close"),
])
def test_each_invalid_case_is_rejected(changes, expected):
    problems = bar_problems(bar(**changes))
    assert any(expected in p for p in problems), problems


def test_quote_bars_keep_ibkr_volume_minus_one_and_volatility_bars_skip_the_price_sign():
    assert bar_problems(bar(volume=-1), "BID") == []                     # IBKR: volume -1 on BID / ASK / MIDPOINT
    vol = {"date": "20261005", "open": 0.21, "high": 0.25, "low": 0.2, "close": 0.22, "volume": -1}
    assert bar_problems(vol, "OPTION_IMPLIED_VOLATILITY") == []
    assert bar_problems({**vol, "low": 0.3}, "OPTION_IMPLIED_VOLATILITY")  # still checked for consistency


def test_split_and_the_import_path_drop_rejected_bars_and_log_them(caplog):
    bad = bar(date="20261005 09:40:00", high=99.0)
    valid, rejected = split_valid_bars([GOOD, bad], "TRADES")
    assert valid == [GOOD] and rejected[0][0] is bad
    with caplog.at_level(logging.WARNING):
        kept = IBKRFactorValueRepository._valid_bars([GOOD, bad], "JPM", "TRADES")
    assert kept == [GOOD]
    assert "IBKR import anomaly JPM TRADES bar 20261005 09:40:00" in caplog.text and "not stored" in caplog.text
    assert IBKRFactorValueRepository._valid_bars(None, "JPM", "TRADES") is None
