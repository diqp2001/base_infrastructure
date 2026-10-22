"""
BI-026: market-data source selection policy (domain) and the IBKR fetch that follows it. No broker: the IBKR
history call is replaced by a fake that answers per data type.
"""

from types import SimpleNamespace

import pytest

from src.domain.entities.factor.observation_quality import SourceDataType as D
from src.domain.entities.factor.source_policy import (
    ANY, DEFAULT_SOURCE_POLICY as P, IntendedUse as U, SourcePolicy, SourceRule, UnsupportedSourceSelection,
)


# ---- policy -----------------------------------------------------------------------------------

@pytest.mark.parametrize("instrument", ["CompanyShareOption", "IndexFuture", "BondFuture", "Index"])
def test_price_marks_are_midpoint_first_then_trades(instrument):
    choice = P.select(instrument, "price", "close", U.VALUATION_MARK)
    assert choice.order == (D.MIDPOINT, D.TRADES) and choice.fallback_allowed


def test_share_price_marks_are_trades_first_then_midpoint():
    """The account has no US-equity quote permission (MIDPOINT refused, BI-037): shares read TRADES first."""
    choice = P.select("CompanyShare", "price", "close", U.VALUATION_MARK)
    assert choice.order == (D.TRADES, D.MIDPOINT) and choice.fallback_allowed


def test_the_intended_use_changes_the_source():
    assert P.select("CompanyShare", "price", "close", U.EXECUTION_PRICE).order == (D.TRADES,)
    assert P.select("CompanyShare", "price", "close", U.MODEL_INPUT).order == (D.TRADES, D.MIDPOINT)
    assert P.select("CompanyShareOption", "price", "close", U.MODEL_INPUT).order == (D.MIDPOINT, D.TRADES)
    assert not P.select("CompanyShare", "price", "close", U.EXECUTION_PRICE).fallback_allowed


def test_volume_and_volatility_have_their_own_types():
    assert P.select("CompanyShare", "price", "volume", U.VALUATION_MARK).order == (D.TRADES,)
    assert P.select("CompanyShareOption", "volatility", "iv", U.MODEL_INPUT, subgroup="implied").order == \
        (D.OPTION_IMPLIED_VOLATILITY,)
    assert P.select("CompanyShare", "volatility", "hv", U.MODEL_INPUT, subgroup="historical").order == \
        (D.HISTORICAL_VOLATILITY,)


def test_an_uncovered_combination_fails_clearly():
    with pytest.raises(UnsupportedSourceSelection, match="no source rule"):
        P.select("CompanyShare", "price", "close", U.FINANCING)


def test_policies_can_differ_by_instrument_class():
    policy = SourcePolicy(rules=(
        SourceRule("Option", "price", ANY, (U.VALUATION_MARK,), (D.BID_ASK, D.MIDPOINT), fallback_allowed=True),
        SourceRule(ANY, "price", ANY, (U.VALUATION_MARK,), (D.TRADES,)),
    ))
    assert policy.select("CompanyShareOption", "price", "close").order == (D.BID_ASK, D.MIDPOINT)
    assert policy.select("CompanyShare", "price", "close").order == (D.TRADES,)


def test_a_rule_states_its_fallback_explicitly():
    with pytest.raises(ValueError, match="fallback_allowed"):
        SourceRule(ANY, "price", ANY, (U.VALUATION_MARK,), (D.MIDPOINT, D.TRADES))


def test_the_selection_note_says_why():
    choice = P.select("CompanyShareOption", "price", "close")
    assert choice.selection_note(D.MIDPOINT).startswith("MIDPOINT: preferred")
    assert choice.selection_note(D.TRADES, (D.MIDPOINT,)).startswith("TRADES: fallback after MIDPOINT returned no data")


# ---- IBKR fetch follows the policy ------------------------------------------------------------

def fetcher(answers):
    """A stand-in IBKR repository whose history call answers per data type; records the calls."""
    from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
    calls = []

    def fetch(symbol, target_date, asset, what_to_show, duration_str, bar_size_setting):
        calls.append(what_to_show)
        return answers.get(what_to_show)
    stub = SimpleNamespace(_fetch_bulk_historical_data=fetch)
    return (lambda choice: IBKRFactorValueRepository._fetch_in_policy_order(stub, "SPY", None, None, choice, "3 D",
                                                                             "8 hours")), calls


def test_the_fetch_uses_midpoint_when_it_answers():
    fetch, calls = fetcher({"MIDPOINT": [{"close": 1}], "TRADES": [{"close": 2}]})
    bars, used, note = fetch(P.select("CompanyShareOption", "price", "close"))
    assert (bars, used, calls) == ([{"close": 1}], "MIDPOINT", ["MIDPOINT"])
    assert note.startswith("MIDPOINT: preferred")


def test_the_fetch_falls_back_to_trades_and_says_so():
    fetch, calls = fetcher({"MIDPOINT": None, "TRADES": [{"close": 2}]})
    bars, used, note = fetch(P.select("CompanyShareOption", "price", "close"))
    assert (used, calls) == ("TRADES", ["MIDPOINT", "TRADES"])
    assert "fallback after MIDPOINT" in note


def test_a_share_fetch_asks_trades_first_and_midpoint_only_without_trades():
    fetch, calls = fetcher({"MIDPOINT": [{"close": 1}], "TRADES": [{"close": 2}]})
    assert fetch(P.select("CompanyShare", "price", "close"))[:2] == ([{"close": 2}], "TRADES") and calls == ["TRADES"]
    fetch, calls = fetcher({"MIDPOINT": [{"close": 1}], "TRADES": None})
    assert fetch(P.select("CompanyShare", "price", "close"))[1] == "MIDPOINT" and calls == ["TRADES", "MIDPOINT"]


def test_no_fallback_when_the_use_forbids_it():
    fetch, calls = fetcher({"TRADES": None, "MIDPOINT": [{"close": 1}]})
    bars, used, note = fetch(P.select("CompanyShare", "price", "close", U.EXECUTION_PRICE))
    assert (bars, used, calls) == (None, None, ["TRADES"])          # a quote never stands in for a trade


def test_what_to_show_follows_the_policy_by_instrument():
    from src.infrastructure.repositories.ibkr_repo.factor.what_to_show import resolve_what_to_show
    share_close = type("CompanyShareFactor", (), {"name": "close", "group": "price", "subgroup": "ohlc"})()
    share = type("CompanyShare", (), {})()
    assert resolve_what_to_show(share_close, share) == "TRADES"
    assert resolve_what_to_show(share_close, share, use=U.EXECUTION_PRICE) == "TRADES"
