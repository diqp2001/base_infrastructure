"""
Which stored bar may stand for the value at a decision time (bar_calendar.bar_is_current), and which IBKR
data type a raw bar is fetched with (ibkr_repo.factor.what_to_show).

Regression (SPX v2, Aug 2026): with a fixed 4-day staleness cap, the option's 10 Aug bar priced the book on
11–14 Aug without any fetch (frozen value), and the option bars were requested as TRADES — a Dec-2028 call
that did not trade gave no bar at all on 17–21 Aug, so its greeks were missing and no hedge was sent.
"""

from datetime import date, datetime, timedelta

import pytest

from src.domain.entities.factor.bar_calendar import (
    bar_is_current, is_trading_day, previous_trading_day, us_market_holidays,
)
from src.infrastructure.repositories.ibkr_repo.factor.what_to_show import resolve_what_to_show

H8, DAY, M5 = 8 * 3600, 86400, 300


def bar(start, seconds, trimmed_at=None):
    close = start + timedelta(seconds=seconds)
    return start, min(close, trimmed_at) if trimmed_at else close


# ---- calendar --------------------------------------------------------------------------------

def test_holidays_and_trading_days():
    assert date(2026, 9, 7) in us_market_holidays(2026)            # Labor Day
    assert date(2026, 4, 3) in us_market_holidays(2026)            # Good Friday
    assert not is_trading_day(date(2026, 8, 15))                   # Saturday
    assert previous_trading_day(date(2026, 9, 8)) == date(2026, 9, 4)   # over the Labor Day weekend


# ---- 8h bars, decision at 16:00 --------------------------------------------------------------

def test_8h_the_days_morning_bar_is_current_at_16():
    start, close = bar(datetime(2026, 8, 11, 9, 30), H8, trimmed_at=datetime(2026, 8, 11, 12, 0))
    assert bar_is_current(start, close, datetime(2026, 8, 11, 16, 0), H8)


def test_8h_yesterdays_bar_is_stale_at_16():
    """The 10 Aug bar must not price 11 Aug: 11 Aug's bar is due (fetch it, or the value is missing)."""
    start, close = bar(datetime(2026, 8, 10, 12, 0), H8)
    assert not bar_is_current(start, close, datetime(2026, 8, 11, 16, 0), H8)
    assert not bar_is_current(start, close, datetime(2026, 8, 17, 16, 0), H8)


def test_8h_before_the_first_bar_closes_the_previous_trading_days_bar_is_current():
    start, close = bar(datetime(2026, 8, 7, 12, 0), H8)                 # Friday afternoon bar
    assert bar_is_current(start, close, datetime(2026, 8, 10, 9, 0), H8)    # Monday before the open
    assert bar_is_current(start, close, datetime(2026, 8, 8, 16, 0), H8)    # Saturday


# ---- daily bars ------------------------------------------------------------------------------

def test_daily_fridays_bar_is_current_on_monday_not_tuesday():
    start, close = bar(datetime(2026, 8, 7), DAY)
    assert bar_is_current(start, close, datetime(2026, 8, 10, 16, 0), DAY)
    assert not bar_is_current(start, close, datetime(2026, 8, 11, 16, 0), DAY)


def test_daily_bar_before_a_holiday_is_current_after_it():
    start, close = bar(datetime(2026, 9, 4), DAY)                       # Friday before Labor Day
    assert bar_is_current(start, close, datetime(2026, 9, 8, 16, 0), DAY)


# ---- 5-minute bars ---------------------------------------------------------------------------

@pytest.mark.parametrize("start, current", [(datetime(2026, 8, 11, 10, 50), True),
                                            (datetime(2026, 8, 11, 10, 40), False),
                                            (datetime(2026, 8, 10, 15, 55), False)])
def test_5min_bar_must_be_the_last_closed_one(start, current):
    s, c = bar(start, M5)
    assert bar_is_current(s, c, datetime(2026, 8, 11, 11, 0), M5) is current


# ---- IBKR data type --------------------------------------------------------------------------

def factor(cls_name, name, group="price", subgroup="ohlc", factor_type=None):
    return type(cls_name, (), {"name": name, "group": group, "subgroup": subgroup, "factor_type": factor_type})()


def test_option_prices_are_midpoint_whatever_the_subgroup():
    option = type("CompanyShareOption", (), {})()
    close = factor("CompanyShareOptionFactor", "close")
    assert resolve_what_to_show(close) == "MIDPOINT"                    # stored subgroup 'ohlc'
    assert resolve_what_to_show(factor("FactorModel", "close", factor_type="company_share_option_factor")) == "MIDPOINT"
    assert resolve_what_to_show(factor("Factor", "close"), option) == "MIDPOINT"


def test_other_types():
    # shares are midpoint-first too since BI-026 (user rule: trades do not happen on every bar)
    assert resolve_what_to_show(factor("CompanyShareFactor", "close")) == "MIDPOINT"
    assert resolve_what_to_show(factor("CompanyShareOptionFactor", "volume")) == "TRADES"
    assert resolve_what_to_show(factor("CompanyShareOptionImpliedVolFactor", "iv", "volatility", "implied")) \
        == "OPTION_IMPLIED_VOLATILITY"
    assert resolve_what_to_show(group="price", subgroup="option") == "MIDPOINT"


def test_trading_days_match_pandas_market_calendars():
    """BI-012: the pure domain calendar equals pandas_market_calendars' NYSE calendar day by day, 2000-2030
    (special closures included). The domain layer stays dependency-free; this test keeps it right."""
    import datetime as dt
    mcal = pytest.importorskip("pandas_market_calendars")
    from src.domain.entities.factor.bar_calendar import is_trading_day
    sched = mcal.get_calendar("NYSE").schedule(start_date="2000-01-01", end_date="2030-12-31")
    open_days = {d.date() for d in sched.index}
    d, diff = dt.date(2000, 1, 1), []
    while d <= dt.date(2030, 12, 31):
        if is_trading_day(d) != (d in open_days):
            diff.append(d)
        d += dt.timedelta(days=1)
    assert diff == []
