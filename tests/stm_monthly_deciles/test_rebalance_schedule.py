"""
The decile cycle on other rebalance periods than the month (deciles.rebalance_every): every N trading days, weeks or
months, one model row per period-end close, the annualisation following the period. Fakes stand for the closes and
the STM scorers (fast).
"""

from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.application.managers.project_managers.stm_monthly_decile_project import config as project_config
from src.application.services.portfolio_research.decile_portfolios import DecileConfig
from src.application.services.portfolio_research.stm_decile_cycle import STMDecileTradingCycle, period_end_panel

MEMBERS = [f"S{i:02d}" for i in range(20)]
DAYS = pd.bdate_range("2024-01-01", "2024-04-30")


class Reader:
    """Closes dated D are known from D+1 (as KnownClosesReader)."""

    def __init__(self):
        rng = np.random.default_rng(3)
        self.frame = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (len(DAYS), len(MEMBERS))), axis=0)),
                                  index=DAYS, columns=MEMBERS)

    def closes(self, now):
        return self.frame.loc[: pd.Timestamp(now).normalize() - pd.Timedelta(days=1)]


class Scorer:
    def __init__(self):
        self.panels = []

    def score(self, panel, members, T):
        self.panels.append(panel)
        return SimpleNamespace(scores={s: float(i) for i, s in enumerate(members)}, unscored=[], trained_at=T,
                               retrained=True, model_assets=members)


def _run(period, every):
    scorer = Scorer()
    cycle = STMDecileTradingCycle(SimpleNamespace(members_at=lambda d: MEMBERS), Reader(), {"A": scorer},
                                  DecileConfig(n_deciles=10), date(2024, 1, 1), date(2024, 12, 31), traded="A",
                                  period=period, every=every)
    rebalances = [r.rebalance for r in (cycle.step(day + pd.Timedelta(hours=16)) for day in DAYS) if r.rebalance]
    return rebalances, scorer


def test_weekly_rebalances_at_each_weeks_last_trading_day():
    rebalances, scorer = _run("W", 1)
    assert all(t.dayofweek == 4 for t in rebalances)                       # Fridays (no holidays in the fake)
    assert all((b - a).days == 7 for a, b in zip(rebalances, rebalances[1:]))
    assert scorer.panels[-1].index[-1] == rebalances[-1]                    # the model's rows are week-end closes
    assert all(d.dayofweek == 4 for d in scorer.panels[-1].index[:-1])


def test_every_two_weeks_skips_one_week_and_daily_rebalances_every_trading_day():
    two, _ = _run("W", 2)
    assert all((b - a).days == 14 for a, b in zip(two, two[1:]))
    daily, _ = _run("D", 1)
    assert len(daily) == len(DAYS) - 1 and daily[0] == DAYS[0]              # the first day's close is known next day


def test_monthly_is_unchanged():
    rebalances, _ = _run("M", 1)
    assert [t.strftime("%Y-%m-%d") for t in rebalances] == ["2024-01-31", "2024-02-29", "2024-03-29"]


def test_period_end_panel_and_the_projects_schedule():
    panel = period_end_panel(Reader().frame, DAYS[-1], "W")
    assert len(panel) == len(set(DAYS.to_period("W")))
    config = {**project_config.DEFAULT_CONFIG,
              "deciles": {**project_config.DEFAULT_CONFIG["deciles"], "rebalance_every": "2w",
                          "retrain_every_rebalances": 2}}
    assert project_config.rebalance_schedule(config) == ("W", 2)
    assert project_config.periods_per_year(config) == 26
    assert project_config.build_stm_configuration(config).features.annualisation == 26
    assert project_config.build_decile_config(config).periods_per_year == 26
    assert project_config.rebalance_labels(config)["retraining"] == "every 4 weeks"
    assert project_config.rebalance_schedule() == ("M", 1)                 # the project's default: monthly
    assert project_config.build_stm_configuration().features.annualisation == 12
    with pytest.raises(ValueError):
        project_config.rebalance_schedule({"deciles": {"rebalance_every": "10m"}})
