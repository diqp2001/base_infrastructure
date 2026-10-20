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
