"""Dispersion screener P.11 (read-only): the fill check of the screened legs on fresh quotes. No broker, no orders."""

import json

from src.application.services.dispersion.paper_validation_service import PaperValidationService
from src.application.services.dispersion.paper_validation_service import LegToCheck, check_leg, fill_check
from src.domain.ports.finance.dispersion.option_data import OptionQuote, Quote
from tests.dispersion.test_dispersion_screening_service import DAY, NOW, SPOTS, FakeMarket, screen

SELL = LegToCheck("ETF", "sell", 2, 100, 5.0)
BUY = LegToCheck("A", "buy", 3, 100, 1.25)


def test_a_leg_fills_when_its_side_is_at_least_as_good():
    assert check_leg(SELL, 5.0, 5.2, 1).would_fill and not check_leg(SELL, 4.9, 5.2, 1).would_fill
    assert check_leg(BUY, 1.1, 1.25, 1).would_fill and not check_leg(BUY, 1.1, 1.3, 1).would_fill
    assert abs(check_leg(SELL, 4.9, 5.2, 1).slippage - 0.1 * 2 * 100) < 1e-9   # sold 0.10 lower, 2 contracts
    assert abs(check_leg(BUY, 1.1, 1.3, 1).slippage - 0.05 * 3 * 100) < 1e-9  # paid 0.05 more, 3 contracts
    assert check_leg(BUY, 1.1, 1.2, 1).slippage < 0                           # better than screened


def test_a_missing_or_frozen_quote_never_counts_as_a_fill():
    assert check_leg(SELL, None, 5.2, 1).problem and not check_leg(SELL, None, 5.2, 1).would_fill
    frozen = check_leg(SELL, 5.1, 5.2, 2)
    assert "not live" in frozen.problem and not frozen.would_fill
    assert check_leg(SELL, 5.1, 5.2, 2, require_live=False).would_fill
    check = fill_check([check_leg(SELL, 5.0, 5.2, 1), check_leg(BUY, None, None, None)])
    assert not check.complete and check.slippage is None and not check.all_fill


def test_the_service_requotes_every_leg_of_a_priced_candidate():
    quotes = {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)}
    c = screen(FakeMarket(SPOTS, quotes), A=0.5, B=0.5)

    class Moved(FakeMarket):                                                  # the ETF bid fell 0.10
        def option_quotes(self, contracts, screening_date):
            out = super().option_quotes(contracts, screening_date)
            k = next(k for k in out if out[k].contract.underlying == "ETF")
            q = out[k]
            out[k] = OptionQuote(q.contract, Quote(bid=4.9, ask=5.1, quote_time=NOW, market_data_type=1), q.greeks)
            return out
    [v] = PaperValidationService(Moved(SPOTS, quotes), now=lambda: NOW).validate([c], DAY)
    assert len(v.check.legs) == 1 + len(c.sizing.positions)
    assert v.check.legs_filled == len(v.check.legs) - 1 and not v.check.all_fill
    assert abs(v.check.slippage - 0.1 * c.sizing.etf_contracts * 100) < 1e-9
    assert abs(v.requoted_net_premium - (c.premium.net_premium - v.check.slippage)) < 1e-9
    row = json.loads(json.dumps(v.row()))
    assert row["legs_would_fill"] == len(v.check.legs) - 1 and row["leg_checks"][0]["side"] == "sell"


def test_unpriced_candidates_are_not_requoted():
    c = screen(FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5)}, no_options=["B"]), A=0.5, B=0.5)
    assert PaperValidationService(FakeMarket(SPOTS, {}), now=lambda: NOW).validate([c], DAY) == []
