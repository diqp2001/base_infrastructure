"""
Checklist section 5 — what the SPX v2 trading cycle sends to set_holdings (fakes only).

``expectedFailure`` tests name a known gap in their docstring.
"""

import math
import unittest

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from tests.market_making_spx_v2.test_spx_v2_project import (
    OPTION, T0, FakePortfolio, FakeStrategy, make_cycle, slice_with,
)


class RejectingPortfolio(FakePortfolio):
    """set_holdings refuses everything (blocked reconciliation, no price, no cash...)."""

    def set_holdings(self, targets, data=None):
        self.calls.append(targets)
        return {spec["name"]: False for value in targets.values()
                for spec in (value if isinstance(value, list) else [value])}


def hedge(target):
    return {"should_hedge": True, "target_hedge_delta": target, "portfolio_delta": 1.2, "hedge_direction": "sell"}


class EntryLegsTest(unittest.TestCase):

    def test_entry_is_one_option_target_sent_once(self):
        portfolio = FakePortfolio()
        make_cycle(portfolio).step(T0, slice_with("SPY", 500.0), portfolio)
        option_calls = [c for c in portfolio.calls if CompanyShareOption in c]
        self.assertEqual(len(option_calls), 1)
        self.assertEqual(option_calls[0], {CompanyShareOption: {"name": OPTION, "weight": -0.2}})

    def test_option_and_hedge_are_separate_calls_so_one_never_liquidates_the_other(self):
        portfolio = FakePortfolio()
        make_cycle(portfolio, strategy=FakeStrategy(hedge=hedge(-120.0))).step(T0, slice_with("SPY", 500.0), portfolio)
        self.assertEqual([set(c) for c in portfolio.calls], [{CompanyShareOption}, {CompanyShare}])

    def test_no_reentry_while_the_option_is_held(self):
        portfolio = FakePortfolio({OPTION: -2})
        cycle = make_cycle(portfolio)
        for _ in range(3):
            cycle.step(T0, slice_with("SPY", 500.0), portfolio)
        self.assertFalse(any(CompanyShareOption in c for c in portfolio.calls))

    @unittest.expectedFailure
    def test_call_spread_entry_sends_both_legs_together(self):
        """GAP: the 'call spread' cycle enters a single short call (naked) — there is no long leg,
        so nothing guarantees a defined-risk position. A spread entry must carry both legs in one
        set_holdings call."""
        portfolio = FakePortfolio()
        make_cycle(portfolio).step(T0, slice_with("SPY", 500.0), portfolio)
        legs = portfolio.calls[0][CompanyShareOption]
        self.assertIsInstance(legs, list)
        self.assertEqual(sorted(math.copysign(1, leg["weight"]) for leg in legs), [-1.0, 1.0])

    @unittest.expectedFailure
    def test_rejected_entry_is_not_reported_as_traded(self):
        """BUG: step() ignores set_holdings' result; a refused entry is still logged and reported
        as option_order / traded."""
        portfolio = RejectingPortfolio()
        result = make_cycle(portfolio).step(T0, slice_with("SPY", 500.0), portfolio)
        self.assertIsNone(result.option_order)
        self.assertFalse(result.traded)


class HedgeGuardTest(unittest.TestCase):

    def test_hedge_quantity_is_the_target_delta(self):
        portfolio = FakePortfolio({OPTION: -2})
        make_cycle(portfolio, strategy=FakeStrategy(hedge=hedge(-120.0))).step(T0, slice_with("SPY", 500.0), portfolio)
        self.assertEqual(portfolio.calls, [{CompanyShare: {"name": "SPY", "quantity": -120.0}}])

    @unittest.expectedFailure
    def test_non_finite_hedge_is_not_sent(self):
        """BUG: a NaN / inf target_hedge_delta (e.g. missing greeks) is passed to set_holdings unchecked."""
        for bad in (math.nan, math.inf):
            portfolio = FakePortfolio({OPTION: -2})
            make_cycle(portfolio, strategy=FakeStrategy(hedge=hedge(bad))).step(T0, slice_with("SPY", 500.0), portfolio)
            self.assertEqual(portfolio.calls, [], f"hedge {bad} was sent")


if __name__ == "__main__":
    unittest.main()
