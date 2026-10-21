"""Data coverage statistics of the STM results report (stm_data_coverage + renderer)."""

from types import SimpleNamespace

import numpy as np
import pytest
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_data_coverage import (
    data_coverage,
    expected_bars,
)


def test_expected_bars_follow_the_nyse_calendar():
    # Thanksgiving 2026-11-26 closed, 2026-11-27 closes at 13:00
    days = expected_bars("2026-11-25", "2026-11-30", None)
    assert list(days.strftime("%m-%d")) == ["11-25", "11-27", "11-30"]
    bars = expected_bars("2026-11-25 09:30", "2026-11-27 15:50", 10)
    assert len(bars) == 39 + 21
    assert bars[0] == pd.Timestamp("2026-11-25 09:30") and bars[-1] == pd.Timestamp("2026-11-27 12:50")


def _panel(index, assets):
    return pd.DataFrame(np.arange(len(index) * len(assets), dtype=float).reshape(len(index), len(assets)) + 100,
                        index=index, columns=assets)


def test_coverage_counts_missing_bars_gaps_off_grid_and_absent_assets():
    history = expected_bars("2026-10-01 09:30", "2026-10-02 15:50", 10)      # 78 bars
    backtest = expected_bars("2026-10-05 09:30", "2026-10-05 15:50", 10)     # 39 bars
    closes = _panel(history.append(backtest), ["AAA", "BBB"])
    closes.loc[backtest[5:9], "BBB"] = np.nan                                 # 4-bar gap in the backtest
    closes.loc[backtest[20], "BBB"] = np.nan                                  # + 1 isolated missing bar
    closes.loc[history[:39], "AAA"] = np.nan                                  # AAA misses the first history day
    closes.loc[pd.Timestamp("2026-10-05 17:00"), "AAA"] = 1.0                 # extended-hours bar: off grid
    closes = closes.sort_index()
    decisions = list(backtest)
    summary, assets, by_session = data_coverage(
        closes, ["AAA", "BBB", "CCC"], decisions, {"AAA": 39, "BBB": 34}, bar_minutes=10,
        history_start="2026-10-01", scored_per_decision=[2] * 34 + [1] * 5)

    a, b, c = assets.loc["AAA"], assets.loc["BBB"], assets.loc["CCC"]
    assert (a["Backtest expected"], a["Backtest present"], a["Backtest missing"]) == (39, 39, 0)
    assert a["History coverage %"] == 50.0 and a["Off-grid bars"] == 0       # 17:00 is after the last decision
    assert (b["Backtest present"], b["Backtest missing"], b["Longest gap (bars)"]) == (34, 5, 4)
    assert round(b["Backtest coverage %"], 2) == round(100 * 34 / 39, 2) and b["Decisions scored"] == 34
    assert c["Backtest present"] == 0 and c["First bar"] == "none" and c["History coverage %"] == 0.0
    assert list(assets.index)[0] == "CCC"                                    # least covered first

    s = summary["Value"]
    assert s["Universe (assets)"] == 3 and s["Expected bars per asset — backtest"] == 39
    assert s["Expected bars per asset — history"] == 78
    assert s["Coverage % — backtest"] == pytest.approx(100 * (39 + 34) / (3 * 39))
    assert s["Coverage % — history"] == pytest.approx(100 * (39 + 78) / (3 * 78))
    assert s["Assets without any stored bar"] == "CCC" and s["Assets fully covered in backtest"] == 1
    assert s["Assets scored per decision (min / mean / max)"] == "1 / 1.9 / 2"
    assert s["Decisions without scores"] == 0
    assert list(by_session.index) == list(pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-05"]))
    assert by_session.iloc[0] == pytest.approx(100 / 3) and by_session.iloc[1] == pytest.approx(200 / 3)


def test_daily_coverage_and_off_grid_bars():
    sessions = expected_bars("2026-09-01", "2026-09-30", None)
    closes = _panel(sessions, ["AAA"])
    closes.loc[pd.Timestamp("2026-09-07"), "AAA"] = 5.0                      # Labor Day: market closed
    closes = closes.sort_index()
    summary, assets, _ = data_coverage(closes, ["AAA"], list(sessions[10:]), {"AAA": 11}, bar_minutes=None)
    assert assets.loc["AAA", "Backtest coverage %"] == 100.0
    assert assets.loc["AAA", "Off-grid bars"] == 1
    assert summary["Value"]["Bar"] == "1 session"


def test_renderer_shows_coverage_and_old_reports_still_render():
    from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_renderer as r
    summary = pd.DataFrame({"Value": pd.Series({"Universe (assets)": 3, "Coverage % — backtest": 93.58974,
                                                "Assets without any stored bar": "CCC"}, dtype=object)})
    rep = SimpleNamespace(coverage_summary=summary, coverage_assets=pd.DataFrame({"Backtest present": [39]}),
                          coverage_by_session=pd.Series([100.0, 50.0], index=pd.to_datetime(["2026-10-01", "2026-10-02"])),
                          period=("2026-10-02", "2026-10-02"), table_raw=pd.DataFrame(), table_rescaled=pd.DataFrame(),
                          table_costs=pd.DataFrame())
    html = r.table_html(dict((k, df) for k, _, df in r.tables(rep))["coverage_summary"])
    assert "93.590" in html and ">3<" in html and "CCC" in html
    assert r.figure_png(rep, "coverage_figure")[:4] == b"\x89PNG"
    old = SimpleNamespace(period=("2026-10-02", "2026-10-02"), table_raw=pd.DataFrame(),
                          table_rescaled=pd.DataFrame(), table_costs=pd.DataFrame())
    tables = dict((k, df) for k, _, df in r.tables(old))
    assert "not available" in tables["coverage_assets"].iloc[0, 0]
    assert r.figure_png(old, "coverage_figure")[:4] == b"\x89PNG"
