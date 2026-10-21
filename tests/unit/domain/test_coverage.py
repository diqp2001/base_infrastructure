"""BI-029: coverage of stored bars against the trading calendar (pure domain)."""

from datetime import date, datetime

from src.domain.entities.factor.coverage import Gap, coverage, expected_days

# Mon 17 Aug 2026 .. Fri 4 Sep 2026; Mon 7 Sep 2026 is Labor Day
AS_OF = datetime(2026, 9, 8, 17, 0)


def bars(*days, hour=0):
    return [datetime(d.year, d.month, d.day, hour) for d in days]


def weekdays(start, end):
    return [d for d in expected_days(start, end, AS_OF)]


def test_a_full_series_is_complete():
    days = weekdays(date(2026, 8, 17), date(2026, 8, 21))
    report = coverage(bars(*days), date(2026, 8, 17), date(2026, 8, 21), AS_OF)
    assert report.is_complete() and report.gaps == () and report.completeness == 1.0


def test_a_partial_response_is_not_complete_coverage():
    """IBKR answered (some bars) but 11..21 Aug style holes remain: detected, listed as one run."""
    days = weekdays(date(2026, 8, 17), date(2026, 8, 28))
    stored = [d for d in days if not date(2026, 8, 19) <= d <= date(2026, 8, 25)]
    report = coverage(bars(*stored), date(2026, 8, 17), date(2026, 8, 28), AS_OF)
    assert report.gaps == (Gap(date(2026, 8, 19), date(2026, 8, 25), 5),)   # the weekend inside does not split it
    assert report.completeness == 5 / 10 and not report.is_complete() and report.is_complete(0.5)


def test_closures_are_not_gaps():
    """Weekends and Labor Day (7 Sep) are not expected."""
    report = coverage(bars(date(2026, 9, 4), date(2026, 9, 8)), date(2026, 9, 4), date(2026, 9, 8), AS_OF)
    assert report.expected == (date(2026, 9, 4), date(2026, 9, 8)) and report.is_complete()


def test_today_is_expected_only_after_the_close():
    start = end = date(2026, 9, 8)
    assert coverage([], start, end, datetime(2026, 9, 8, 15, 59)).expected == ()
    assert coverage([], start, end, datetime(2026, 9, 8, 16, 0)).gaps == (Gap(start, end, 1),)


def test_overlapping_downloads_count_once():
    days = weekdays(date(2026, 8, 17), date(2026, 8, 21))
    report = coverage(bars(*days) + bars(*days[:3]) + bars(*days, hour=12), date(2026, 8, 17), date(2026, 8, 21),
                      AS_OF)
    assert report.received == tuple(days) and report.completeness == 1.0


def test_bars_on_closed_days_are_reported_not_counted():
    report = coverage(bars(date(2026, 9, 7)), date(2026, 9, 4), date(2026, 9, 8), AS_OF)
    assert report.unexpected == (date(2026, 9, 7),) and report.received == ()
    assert "0/2 trading days" in report.summary()


def test_intraday_bars_cover_their_day():
    report = coverage([datetime(2026, 9, 4, 9, 30), datetime(2026, 9, 4, 12, 0)], date(2026, 9, 4), date(2026, 9, 4),
                      AS_OF)
    assert report.is_complete()
