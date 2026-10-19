"""
Returns, mid prices, holding values and bond-future yields — exact expected values plus
Hypothesis invariants (scaling, bounds, round trips).
"""

import math
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_roll_yield_factor import (
    BondFutureAnnualizedRollYieldFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_yield_factor import (
    BondFutureAnnualizedYieldFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_discounted_value_factor import (
    BondFutureDiscountedValueFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_forward_price_factor import (
    BondFutureForwardPriceFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import (
    CompanyShareOptionPriceReturnFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import (
    CompanyShareMidPriceFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import (
    CompanySharePriceReturnFactor,
)
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import (
    CompanySharePortfolioHoldingValueFactor,
)


def make(cls, **metadata):
    try:
        return cls()
    except TypeError:
        return cls(**metadata)


price = st.floats(min_value=0.01, max_value=1e6)
scale = st.floats(min_value=1e-3, max_value=1e3)


class TestShareReturns:
    factor = make(CompanySharePriceReturnFactor, name="return", group="return", subgroup="daily", frequency="1d")

    @pytest.mark.parametrize("start,end,expected", [(100, 110, 0.10), (100, 90, -0.10), (50, 50, 0.0), (4, 1, -0.75)])
    def test_simple_return(self, start, end, expected):
        assert self.factor.calculate(start, end) == pytest.approx(expected)
        assert self.factor.calculate(start, end, method="simple") == pytest.approx(expected)

    @pytest.mark.parametrize("start,end", [(0, 10), (10, 0), (-1, 10), (10, -5)])
    def test_non_positive_prices_have_no_return(self, start, end):
        assert self.factor.calculate(start, end) is None

    def test_unknown_method_fails_loudly(self):
        with pytest.raises(ValueError):
            self.factor.calculate(100, 110, method="log")

    @pytest.mark.property
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    @given(start=price, end=price, k=scale)
    def test_return_is_scale_invariant(self, start, end, k):
        assert self.factor.calculate(start * k, end * k) == pytest.approx(self.factor.calculate(start, end), rel=1e-9, abs=1e-12)

    @pytest.mark.property
    @given(p=price)
    def test_equal_prices_give_zero_return(self, p):
        assert self.factor.calculate(p, p) == 0.0

    @pytest.mark.property
    @settings(max_examples=200)
    @given(a=price, b=price, c=price)
    def test_returns_compound(self, a, b, c):
        ab, bc, ac = self.factor.calculate(a, b), self.factor.calculate(b, c), self.factor.calculate(a, c)
        # (b/a - 1) + 1 cancels catastrophically for extreme ratios: relative error ~ eps * a/b
        tolerance = 1e-12 * max(a / b, b / a, b / c, c / b, 1.0)
        assert (1 + ab) * (1 + bc) == pytest.approx(1 + ac, rel=max(tolerance, 1e-12))


class TestOptionReturns:
    factor = make(CompanyShareOptionPriceReturnFactor, name="price_return", group="return", subgroup="daily")

    def test_simple_and_log_return(self):
        assert self.factor.calculate(current_price=12.0, previous_price=10.0) == pytest.approx(0.2)
        assert self.factor.calculate_log_return(current_price=12.0, previous_price=10.0) == pytest.approx(math.log(1.2))

    def test_option_can_expire_worthless(self):
        """A zero option price is a valid -100 % simple return (no log return)."""
        assert self.factor.calculate(current_price=0.0, previous_price=2.5) == pytest.approx(-1.0)
        assert self.factor.calculate_log_return(current_price=0.0, previous_price=2.5) is None

    @pytest.mark.property
    @given(p0=price, p1=price)
    def test_log_return_is_log_of_gross_simple_return(self, p0, p1):
        assert self.factor.calculate_log_return(p1, p0) == pytest.approx(math.log1p(self.factor.calculate(p1, p0)),
                                                                        rel=1e-9, abs=1e-12)


class TestMidPrice:
    factor = CompanyShareMidPriceFactor()

    def deps(self, *values):
        return {"CompanyShareFactor": list(values)}

    def test_single_source(self):
        if self.factor.min_sources > 1:
            pytest.skip("configured with min_sources > 1")
        assert self.factor.calculate(self.deps(150.0)) == Decimal("150.0")

    def test_below_min_sources_is_none(self):
        assert self.factor.calculate(self.deps(*([150.0] * (self.factor.min_sources - 1)))) is None
        assert self.factor.calculate({}) is None

    def test_median_of_many_and_outlier_is_dropped(self):
        # median 100.5, MAD 0.5: 500 has modified z = 539 > 2 and is dropped; median of the rest
        assert self.factor.calculate(self.deps(100.0, 101.0, 100.2, 100.5, 500.0)) == Decimal("100.35")

    def test_outlier_threshold_is_strict(self):
        # 99.0 has modified z = 1.5 / (1.4826 * 0.5) = 2.02 > 2.0: dropped together with 500
        assert self.factor.calculate(self.deps(100.0, 101.0, 99.0, 100.5, 500.0)) == Decimal("100.5")

    def test_none_values_are_ignored(self):
        assert self.factor.calculate(self.deps(None, 100.0, 102.0, None, 101.0)) == Decimal("101.0")

    @pytest.mark.property
    @settings(max_examples=200)
    @given(values=st.lists(price, min_size=3, max_size=12))
    def test_mid_price_lies_within_the_observed_range(self, values):
        mid = self.factor.calculate(self.deps(*values))
        assert Decimal(str(min(values))) <= mid <= Decimal(str(max(values)))

    @pytest.mark.property
    @settings(max_examples=200)
    @given(values=st.lists(st.floats(min_value=1.0, max_value=1e4), min_size=3, max_size=9), k=st.integers(2, 100))
    def test_mid_price_scales_with_prices(self, values, k):
        base = self.factor.calculate(self.deps(*values))
        scaled = self.factor.calculate(self.deps(*[v * k for v in values]))
        assert float(scaled) == pytest.approx(float(base) * k, rel=1e-9)


class TestHoldingValue:
    factor = CompanySharePortfolioHoldingValueFactor()

    @pytest.mark.parametrize("prices,qty,expected", [([150.0], 10, Decimal("1500.0")), ([150.0], -3, Decimal("-450.0")),
                                                     ([99.99], 0, Decimal("0")), ([0.1], 3, Decimal("0.3"))])
    def test_value_is_price_times_quantity_exactly(self, prices, qty, expected):
        assert self.factor.calculate({"CompanyShareValueFactor": prices, "Position": qty}) == expected

    @pytest.mark.parametrize("deps", [{}, {"Position": 10}, {"CompanyShareValueFactor": [], "Position": 10},
                                      {"CompanyShareValueFactor": [150.0]}])
    def test_missing_price_or_quantity_is_none_not_zero(self, deps):
        assert self.factor.calculate(deps) is None


class TestBondFutureYields:
    forward = BondFutureForwardPriceFactor()
    discount = BondFutureDiscountedValueFactor()
    roll = BondFutureAnnualizedRollYieldFactor()
    implied = BondFutureAnnualizedYieldFactor()

    def test_sofr_future_implied_rate(self):
        assert float(self.implied.calculate({"BondFutureFactor": [96.25]})) == pytest.approx(0.0375)
        assert float(self.implied.calculate({"BondFutureFactor": [96.20, 96.30]})) == pytest.approx(0.0375)
        assert self.implied.calculate({"BondFutureFactor": []}) is None

    def test_forward_price_and_discounting(self):
        assert self.forward.calculate_forward_price(100.0, r=0.05, T=0.5) == pytest.approx(100 * math.exp(0.025))
        assert self.forward.calculate_forward_price(100.0, r=0.05, T=0.5, carry_cost=0.01, coupon_yield=0.03) == \
            pytest.approx(100 * math.exp((0.05 + 0.01 - 0.03) * 0.5))
        assert self.discount.calculate_discounted_value(105.0, r=0.04, T=2.0) == pytest.approx(105 * math.exp(-0.08))

    def test_roll_yield(self):
        assert self.roll.calculate_roll_yield(100.0, 101.0, T=0.25) == pytest.approx(0.04)
        assert self.roll.calculate_roll_yield(0.0, 101.0, T=0.25) is None

    @pytest.mark.property
    @settings(max_examples=200)
    @given(spot=price, r=st.floats(min_value=-0.02, max_value=0.2), T=st.floats(min_value=0.01, max_value=10))
    def test_discounting_the_forward_returns_the_spot(self, spot, r, T):
        fwd = self.forward.calculate_forward_price(spot, r=r, T=T)
        assert self.discount.calculate_discounted_value(fwd, r=r, T=T) == pytest.approx(spot, rel=1e-9)

    def test_rate_and_maturity_are_inputs_not_constants(self):
        """Regression: calculate() used a hard-coded r=5.3 % and T=0.25 when they were not supplied."""
        from datetime import date, datetime
        from types import SimpleNamespace
        future = SimpleNamespace(expiration_date=None, end_date=date(2027, 1, 1))
        when = datetime(2026, 1, 1, 16, 0)                                  # 365 days to expiry
        assert self.forward.calculate({"prices": [100.0], "entity": future, "target_date": when}) is None
        assert self.discount.calculate({"prices": [100.0], "entity": future, "target_date": when}) is None
        assert self.discount.calculate({"prices": [100.0], "rates": [0.02], "target_date": when}) is None
        assert self.roll.calculate({"start_price": 100.0, "end_price": 101.0}) is None
        full = {"prices": [100.0], "rates": [0.02], "entity": future, "target_date": when}
        assert float(self.forward.calculate(full)) == pytest.approx(100 * math.exp(0.02))
        assert float(self.discount.calculate(full)) == pytest.approx(100 * math.exp(-0.02))
        assert float(self.roll.calculate({"start_price": 100.0, "end_price": 101.0, "time_to_maturity": 0.5})) == \
            pytest.approx(0.02)
