"""BI-027: quote validation and freshness (pure domain)."""

from datetime import datetime, timedelta

import pytest

from src.domain.entities.factor.observation_quality import (
    ObservationProvenance, ObservationRef, ObservationStatus as S, QualityRequirement, SourceDataType as D,
)
from src.domain.entities.factor.quote_validation import (
    DAILY, ILLIQUID_OPTION, INTRADAY_LIQUID, Quote, QuotePolicy, check_price_move, status_from, validate_bar_value,
    validate_quote,
)

T = datetime(2026, 8, 24, 16, 0)


def failed(results):
    return {r.rule: r.reason for r in results if not r.passed}


def test_a_good_quote_passes():
    results = validate_quote(Quote(99.95, 100.05, T), INTRADAY_LIQUID, T)
    assert failed(results) == {} and status_from(results) is S.VALID


def test_stale_quote():
    results = validate_quote(Quote(99.95, 100.05, T - timedelta(hours=1)), INTRADAY_LIQUID, T)
    assert failed(results) == {"fresh": "stale: 1:00:00 old > 0:15:00"}
    assert validate_quote(Quote(99.95, 100.05, T - timedelta(hours=1)), DAILY, T) and \
        failed(validate_quote(Quote(99.95, 100.05, T - timedelta(hours=1)), DAILY, T)) == {}   # fine for daily use


def test_a_quote_after_the_decision_time_is_not_fresh():
    assert "after the decision time" in failed(validate_quote(Quote(1, 1.1, T + timedelta(seconds=1)), DAILY, T))["fresh"]


def test_crossed_market():
    assert failed(validate_quote(Quote(100.2, 100.0, T), DAILY, T)) == {"not_crossed": "crossed: bid 100.2 > ask 100.0"}


@pytest.mark.parametrize("quote, rule", [(Quote(None, 100.0, T), "bid_present"), (Quote(99.0, None, T), "ask_present"),
                                         (Quote(0.0, 100.0, T), "bid_positive"), (Quote(99.0, 0.0, T), "ask_positive")])
def test_missing_sides_and_zero_placeholders(quote, rule):
    assert rule in failed(validate_quote(quote, DAILY, T))
    assert status_from(validate_quote(quote, DAILY, T)) is S.INVALID


def test_wide_spread_depends_on_the_policy():
    wide = Quote(1.00, 1.20, T)                                         # ~1818 bps: typical of a long-dated option
    assert "max_spread_bps" in failed(validate_quote(wide, INTRADAY_LIQUID, T))
    assert failed(validate_quote(wide, ILLIQUID_OPTION, T)) == {}
    assert "max_spread_abs" in failed(validate_quote(wide, QuotePolicy(max_spread_abs=0.05), T))


def test_a_legitimate_large_move_is_flagged_not_rejected():
    results = check_price_move(100.0, 130.0, DAILY)
    assert status_from(results) is S.VALID
    assert results[0].passed and results[0].reason.startswith("flag: moved 30.0%")
    assert check_price_move(100.0, 101.0, DAILY)[0].reason == ""


def test_bar_values():
    assert failed(validate_bar_value("150.5", is_price=True)) == {}
    assert failed(validate_bar_value("0.0", is_price=True)) == {"positive_price": "price 0.0 <= 0"}
    assert failed(validate_bar_value("0", is_price=False)) == {}          # a zero volume is a real observation
    assert failed(validate_bar_value("nan", is_price=False)) == {"finite": "value 'nan' is not finite"}
    assert "numeric" in failed(validate_bar_value("n/a", is_price=True))


def test_invalid_quotes_cannot_enter_calculations_that_require_valid_ones():
    results = validate_quote(Quote(100.2, 100.0, T), DAILY, T)
    provenance = ObservationProvenance(observation=ObservationRef(1, "CompanyShare", 5, T), field="close", source="ibkr",
                                       data_type=D.BID_ASK, frequency="1d", status=status_from(results),
                                       validations=tuple(results))
    assert not QualityRequirement().check(provenance, T)


def test_ohlc_consistency():
    from src.domain.entities.factor.quote_validation import validate_ohlc
    assert failed(validate_ohlc(dict(open="100", high="102", low="99", close="101"))) == {}
    assert failed(validate_ohlc(dict(open=100, high=98, low=99, close=99))) == {
        "high_ge_low": "high 98.0 < low 99.0", "open_within_range": "open 100.0 outside [99.0, 98.0]",
        "close_within_range": "close 99.0 outside [99.0, 98.0]"}
    assert failed(validate_ohlc(dict(open=100, high=110, low=95, close=111))) == {
        "close_within_range": "close 111.0 outside [95.0, 110.0]"}
    assert validate_ohlc(dict(open=100, high=110, low=95)) == []                  # incomplete: not judged
    assert validate_ohlc(dict(open="0", high=110, low=95, close=100)) == []       # placeholder: validate_bar_value's


@pytest.mark.parametrize("price, right, rule", [
    (4.0, "C", "option_lower_bound"),     # S 110, K 100: intrinsic 10 (stale underlying or wrong strike)
    (120.0, "C", "option_upper_bound"),   # a call above the share itself
    (101.0, "P", "option_upper_bound"),   # a put above the strike
])
def test_option_prices_outside_no_arbitrage_bounds_are_findings(price, right, rule):
    from src.domain.entities.factor.quote_validation import validate_option_price
    assert rule in failed(validate_option_price(price, 110.0, 100.0, right))


def test_option_prices_inside_the_bounds_pass():
    from src.domain.entities.factor.quote_validation import validate_option_price
    assert failed(validate_option_price(12.5, 110.0, 100.0, "CALL", discount_factor=0.99)) == {}
    assert failed(validate_option_price(0.05, 110.0, 100.0, "P")) == {}                # deep OTM put, cheap: fine
    assert failed(validate_option_price(9.98, 110.0, 100.0, "C", tolerance=0.05)) == {}  # within quote noise
    assert "option_right" in failed(validate_option_price(1.0, 110.0, 100.0, "X"))
