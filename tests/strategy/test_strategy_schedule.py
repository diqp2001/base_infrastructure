"""
Trading and training frequency as category + count (Frequency), stored where each project reads it
(strategy_schedule): intraday decision minutes, daily engine steps, retrain_every_days, monthly decile rebalances.
"""

import pytest

from src.application.services.strategy.strategy_schedule import schedule, schedule_changes
from src.domain.entities.strategy.frequency import Frequency
from src.domain.entities.strategy.strategy import Strategy


def test_frequency_tokens_labels_and_conversions():
    assert Frequency.parse("2w") == Frequency("weeks", 2) and Frequency.parse("3mo").token == "3mo"
    assert Frequency.parse("10m").minutes == 10 and Frequency("hours", 2).minutes == 120
    assert Frequency.from_minutes(120) == Frequency("hours", 2) and Frequency.from_minutes(45) == Frequency("minutes", 45)
    assert Frequency.from_days(30) == Frequency("months", 1) and Frequency.from_days(21) == Frequency("weeks", 3)
    assert Frequency.from_days(10) == Frequency("days", 10) and Frequency("months", 2).days == 60
    assert Frequency("weeks", 2).label == "every 2 weeks" and Frequency("days", 1).label == "every day"
    assert Frequency.parse("") is None and Frequency.parse("fortnight") is None
    with pytest.raises(ValueError):
        Frequency("years", 1)
    with pytest.raises(ValueError):
        Frequency.of("days", "0")


def _strategy(sections, retrain_every_days=None):
    return Strategy(name="s", strategy_type="p", sections=sections, retrain_every_days=retrain_every_days)


def test_a_daily_project_trades_every_n_days_or_weeks_and_retrains_in_calendar_days():
    s = _strategy({"trading": {"bar_size_setting": "1 day", "config_interval": {"custom_interval_days": 1}}},
                  retrain_every_days=21)
    plan = schedule(s)
    assert [u for u, _ in plan["trading"]["units"]] == ["days", "weeks"]
    assert plan["trading"]["current"] == Frequency("days", 1)
    assert plan["training"]["current"] == Frequency("weeks", 3)
    sections, typed = schedule_changes(s, trading=Frequency("weeks", 2), training=Frequency("months", 1))
    assert sections["trading"]["config_interval"] == {"custom_interval_days": 14}
    assert sections["trading"]["bar_size_setting"] == "1 day" and typed == {"retrain_every_days": 30}
    with pytest.raises(ValueError, match="cannot run every 10 minutes"):
        schedule_changes(s, trading=Frequency("minutes", 10))


def test_an_intraday_project_trades_in_minutes_or_hours():
    s = _strategy({"trading": {"config_interval": {"custom_interval_minutes": 10, "session_start": "09:40"}}},
                  retrain_every_days=1)
    assert schedule(s)["trading"]["current"] == Frequency("minutes", 10)
    sections, _ = schedule_changes(s, trading=Frequency("hours", 1))
    assert sections["trading"]["config_interval"] == {"custom_interval_minutes": 60, "session_start": "09:40"}


def test_the_decile_project_rebalances_every_n_days_weeks_or_months_and_retrains_every_n_rebalances():
    s = _strategy({"trading": {"bar_size_setting": "1 day", "config_interval": {"custom_interval_days": 1}},
                   "portfolio": {"deciles": {"n_deciles": 10, "retrain_every_rebalances": 1}}})
    plan = schedule(s)                                                   # no rebalance_every yet: monthly
    assert plan["trading"]["editable"] and plan["trading"]["current"] == Frequency("months", 1)
    assert [u for u, _ in plan["trading"]["units"]] == ["days", "weeks", "months"]
    assert [u for u, _ in plan["training"]["units"]] == ["days", "weeks", "months"]
    assert plan["training"]["follows"] == "trading"                     # the page greys out the more frequent ones
    # weekly trading, retrained every month (21 / 5 trading days -> 4 rebalances)
    sections, typed = schedule_changes(s, trading=Frequency("weeks", 1), training=Frequency("months", 1))
    deciles = sections["portfolio"]["deciles"]
    assert deciles["rebalance_every"] == "1w" and deciles["retrain_every_rebalances"] == 4 and typed == {}
    assert "rebalance_every" not in s.section("portfolio")["deciles"]      # the strategy is not mutated
    s.update(sections=sections)
    plan = schedule(s)
    assert plan["trading"]["current"] == Frequency("weeks", 1)
    assert plan["training"]["current"] == Frequency("weeks", 4)
    sections, _ = schedule_changes(s, training=Frequency("weeks", 2))
    assert sections["portfolio"]["deciles"]["retrain_every_rebalances"] == 2
    with pytest.raises(ValueError, match="more often than trading"):
        schedule_changes(s, training=Frequency("days", 3))
    with pytest.raises(ValueError, match="cannot run every 10 minutes"):
        schedule_changes(s, trading=Frequency("minutes", 10))


def test_a_project_without_schedule_keys_offers_nothing():
    plan = schedule(_strategy({"trading": {"bar_size_setting": "8 hours"}}))
    assert not plan["trading"]["editable"] and not plan["training"]["editable"]
