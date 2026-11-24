"""S&P 500 backtest turnover features (2026-11-24): each month end's value = the domain factor's calculate() on the
stock's last volumes and the share count published BEFORE that month end (never a later filing)."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from src.application.services.model_evaluation.sp500_monthly_backtest import turnover_features
from src.domain.ports.factor.financial_statement_source_port import StatementRecord


class Balance:
    STATEMENT, FREQUENCIES = "balance_sheet", ("1q",)

    def __init__(self, counts):
        self.counts = counts                          # [(available_by, shares)]

    def fetch(self, symbol, frequency):
        return [StatementRecord(symbol=symbol, statement=self.STATEMENT, frequency=frequency, period="Q1",
                                fiscal_year=a.year, period_end=a.date(), filing_date=a.date(), accepted_at=None,
                                reported_currency="USD", cik=None, values={"commonStockSharesOutstanding": n},
                                available_by=a) for a, n in self.counts]


def test_turnover_uses_the_share_count_known_at_each_month_end():
    days = pd.bdate_range("2024-01-01", "2024-03-29")
    volume = pd.DataFrame({"X": np.r_[np.full(len(days) - 5, 1e6), np.full(5, 3e6)]}, index=days)
    panels = {"volume": volume}
    sources = {"balance_sheet": Balance([(datetime(2024, 1, 10), 1e8), (datetime(2024, 3, 29, 0, 0, 1), 2e8)])}
    month_ends = pd.DatetimeIndex(["2024-01-31", "2024-02-29", "2024-03-29"])
    out = turnover_features(panels, ["X"], month_ends, log=lambda m: None, sources=sources)
    # March 29: the 2e8 count is stamped after that day's start -> still 1e8 (no look-ahead)
    assert out.loc[(pd.Timestamp("2024-03-29"), "X"), "turnover_5d"] == pytest.approx(3e6 / 1e8)
    assert out.loc[(pd.Timestamp("2024-02-29"), "X"), "turnover_1m"] == pytest.approx(1e6 / 1e8)
    assert np.isnan(out.loc[(pd.Timestamp("2024-01-31"), "X"), "turnover_3m"])     # 63 sessions not yet there


def test_no_share_count_published_yet_gives_no_row():
    days = pd.bdate_range("2024-01-01", "2024-01-31")
    panels = {"volume": pd.DataFrame({"X": np.full(len(days), 1e6)}, index=days)}
    out = turnover_features(panels, ["X"], pd.DatetimeIndex(["2024-01-31"]), log=lambda m: None,
                            sources={"balance_sheet": Balance([(datetime(2024, 2, 15), 1e8)])})
    assert out.empty and "turnover_5d" in out.columns
