"""BI-013: gaps inside an IBKR answer are reported at import (no IBKR, no DB)."""

import logging
from datetime import datetime

from src.domain.entities.factor.coverage import Gap
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository

report = IBKRFactorValueRepository._report_import_gaps


def test_a_partial_answer_is_reported(caplog):
    bars = [datetime(2026, 8, d, 16) for d in (17, 18, 24, 25)]          # 19..21 Aug missing
    with caplog.at_level(logging.WARNING):
        r = report(bars, "CompanyShareOption", 6, "MIDPOINT")
    assert r.gaps == (Gap(datetime(2026, 8, 19).date(), datetime(2026, 8, 21).date(), 3),)
    assert "CompanyShareOption:6 (MIDPOINT)" in caplog.text and "4/7 trading days" in caplog.text


def test_weekends_holidays_and_intraday_stamps_are_not_gaps(caplog):
    bars = [datetime(2026, 9, 4, 9, 30), datetime(2026, 9, 4, 12), datetime(2026, 9, 8, 9, 30)]   # Labor Day 7 Sep
    with caplog.at_level(logging.WARNING):
        assert report(bars, "CompanyShare", 1).gaps == ()
    assert caplog.text == ""


def test_fewer_than_two_bars_says_nothing():
    assert report([datetime(2026, 9, 4)], "CompanyShare", 1) is None
    assert report([None], "CompanyShare", 1) is None
