"""
Option pricing and Greeks (CompanyShareOption* factors), checked against independent results:

- textbook values: Hull, Options, Futures and Other Derivatives — Example 15.6
  (S=42, K=40, r=10 %, sigma=20 %, T=0.5: call 4.76, put 0.81);
- put-call parity with dividends, for any valid inputs (Hypothesis);
- every Greek against a central finite difference of the BSM price;
- CRR binomial tree converges to BSM; an American put is worth at least the European put.
"""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import (
    CompanyShareOptionBlackScholesMertonPriceFactor as BSM,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_cox_ross_rubinstein_price_factor import (
    CompanyShareOptionCoxRossRubinsteinPriceFactor as CRR,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor import (
    CompanyShareOptionDeltaFactor as Delta,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import (
    CompanyShareOptionGammaFactor as Gamma,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import (
    CompanyShareOptionRhoFactor as Rho,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor import (
    CompanyShareOptionVegaFactor as Vega,
)

def make(cls, **library_metadata):
    """Real constructors; pricing models need the library's name / group / subgroup."""
    try:
        return cls()
    except TypeError:
        return cls(**library_metadata)


bsm = make(BSM, name="black_scholes_merton_price", group="price_model", subgroup="black_scholes")
crr = make(CRR, name="cox_ross_rubinstein_price", group="price_model", subgroup="binomial_tree")
delta, gamma, vega, rho = make(Delta), make(Gamma), make(Vega), make(Rho, name="rho", group="greek")

# realistic but wide input ranges for property tests
spot = st.floats(min_value=1.0, max_value=5_000.0)
moneyness = st.floats(min_value=0.5, max_value=2.0)
rate = st.floats(min_value=-0.01, max_value=0.15)
vol = st.floats(min_value=0.05, max_value=1.5)
maturity = st.floats(min_value=0.02, max_value=5.0)
dividend = st.floats(min_value=0.0, max_value=0.08)


def price(S, K, r, sigma, T, q=0.0, kind="call"):
    return bsm.calculate(S=S, K=K, r=r, sigma=sigma, T=T, q=q, option_type=kind)


class TestBlackScholesMerton:

    def test_hull_example(self):
        assert price(42, 40, 0.10, 0.20, 0.5) == pytest.approx(4.76, abs=0.005)
        assert price(42, 40, 0.10, 0.20, 0.5, kind="put") == pytest.approx(0.81, abs=0.005)

    def test_dividend_lowers_call_and_raises_put(self):
        assert price(100, 100, 0.05, 0.2, 1, q=0.03) < price(100, 100, 0.05, 0.2, 1)
        assert price(100, 100, 0.05, 0.2, 1, q=0.03, kind="put") > price(100, 100, 0.05, 0.2, 1, kind="put")

    @pytest.mark.parametrize("bad", [dict(S=0), dict(K=0), dict(sigma=0), dict(T=0), dict(S=-1), dict(T=-0.5)])
    def test_invalid_inputs_return_none(self, bad):
        args = dict(S=100, K=100, r=0.05, sigma=0.2, T=1.0)
        args.update(bad)
        assert bsm.calculate(**args) is None

    @pytest.mark.parametrize("kind", ["call", "CALL", "Call", "C", "c"])
    def test_call_spellings_including_ibkr_right(self, kind):
        assert price(100, 100, 0.05, 0.2, 1, kind=kind) == pytest.approx(price(100, 100, 0.05, 0.2, 1))

    @pytest.mark.parametrize("kind", ["put", "PUT", "P", "p"])
    def test_put_spellings_including_ibkr_right(self, kind):
        assert price(100, 100, 0.05, 0.2, 1, kind=kind) == pytest.approx(price(100, 100, 0.05, 0.2, 1, kind="put"))

    @pytest.mark.parametrize("kind", ["calls", "", None, "straddle"])
    def test_unknown_option_type_is_not_priced(self, kind):
        """Regression: anything that was not 'call' used to be priced as a put — including the
        IBKR right 'C', which valued calls as puts."""
        assert price(100, 100, 0.05, 0.2, 1, kind=kind) is None
        assert crr.calculate(S=100, K=100, r=0.05, sigma=0.2, T=1, option_type=kind, steps=50) is None
        assert delta.compute_delta(100, 100, 0.05, 0.2, 1, option_type=kind) is None
        assert rho.calculate(S=100, K=100, r=0.05, sigma=0.2, T=1, option_type=kind) is None

    def test_ibkr_right_c_is_a_call_for_every_greek_and_model(self):
        """Regression: delta of an option whose entity stores the IBKR right 'C' was a put delta."""
        assert delta.compute_delta(100, 100, 0.05, 0.2, 1, option_type="C") == pytest.approx(
            delta.compute_delta(100, 100, 0.05, 0.2, 1, option_type="call"))
        assert crr.calculate(S=100, K=100, r=0.05, sigma=0.2, T=1, option_type="C", steps=50) == pytest.approx(
            crr.calculate(S=100, K=100, r=0.05, sigma=0.2, T=1, option_type="call", steps=50))

    @pytest.mark.property
    @settings(max_examples=300, deadline=None)
    @given(S=spot, m=moneyness, r=rate, sigma=vol, T=maturity, q=dividend)
    def test_put_call_parity(self, S, m, r, sigma, T, q):
        K = S * m
        call, put = price(S, K, r, sigma, T, q), price(S, K, r, sigma, T, q, "put")
        assert call - put == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), rel=1e-7, abs=1e-7 * S)

    @pytest.mark.property
    @settings(max_examples=300, deadline=None)
    @given(S=spot, m=moneyness, r=rate, sigma=vol, T=maturity, q=dividend)
    def test_no_arbitrage_bounds(self, S, m, r, sigma, T, q):
        K = S * m
        call, put = price(S, K, r, sigma, T, q), price(S, K, r, sigma, T, q, "put")
        tol = 1e-9 * S
        assert max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0) - tol <= call <= S * math.exp(-q * T) + tol
        assert max(K * math.exp(-r * T) - S * math.exp(-q * T), 0.0) - tol <= put <= K * math.exp(-r * T) + tol

    @pytest.mark.property
    @settings(max_examples=200, deadline=None)
    @given(S=spot, m=moneyness, r=rate, sigma=vol, T=maturity)
    def test_call_increases_with_volatility_and_spot(self, S, m, r, sigma, T):
        K = S * m
        assert price(S, K, r, sigma * 1.1, T) >= price(S, K, r, sigma, T) - 1e-9 * S
        assert price(S * 1.01, K, r, sigma, T) >= price(S, K, r, sigma, T) - 1e-9 * S


class TestGreeks:
    """Analytic Greeks against central finite differences of the BSM price."""

    CASES = [(100, 100, 0.05, 0.2, 1.0, 0.0), (42, 40, 0.10, 0.20, 0.5, 0.0),
             (500, 600, 0.03, 0.35, 2.0, 0.02), (50, 40, 0.01, 0.6, 0.1, 0.0)]

    @pytest.mark.parametrize("S,K,r,sigma,T,q", CASES)
    @pytest.mark.parametrize("kind", ["call", "put"])
    def test_delta(self, S, K, r, sigma, T, q, kind):
        h = S * 1e-4
        fd = (price(S + h, K, r, sigma, T, q, kind) - price(S - h, K, r, sigma, T, q, kind)) / (2 * h)
        assert delta.compute_delta(S, K, r, sigma, T, option_type=kind, dividend_yield=q) == pytest.approx(fd, abs=1e-6)

    @pytest.mark.parametrize("S,K,r,sigma,T,q", CASES)
    def test_gamma(self, S, K, r, sigma, T, q):
        h = S * 1e-3
        fd = (price(S + h, K, r, sigma, T, q) - 2 * price(S, K, r, sigma, T, q) + price(S - h, K, r, sigma, T, q)) / h ** 2
        assert gamma.compute_gamma(S, K, r, sigma, T, dividend_yield=q) == pytest.approx(fd, rel=1e-4, abs=1e-8)

    @pytest.mark.parametrize("S,K,r,sigma,T,q", CASES)
    def test_vega_is_per_unit_of_volatility(self, S, K, r, sigma, T, q):
        h = 1e-5
        fd = (price(S, K, r, sigma + h, T, q) - price(S, K, r, sigma - h, T, q)) / (2 * h)
        assert vega.compute_vega(S, K, r, sigma, T, dividend_yield=q) == pytest.approx(fd, rel=1e-5)

    @pytest.mark.parametrize("S,K,r,sigma,T,q", [c for c in CASES if c[5] == 0.0])
    @pytest.mark.parametrize("kind", ["call", "put"])
    def test_rho_is_per_unit_of_rate(self, S, K, r, sigma, T, q, kind):
        h = 1e-6
        fd = (price(S, K, r + h, sigma, T, 0, kind) - price(S, K, r - h, sigma, T, 0, kind)) / (2 * h)
        assert rho.calculate(S=S, K=K, r=r, sigma=sigma, T=T, option_type=kind) == pytest.approx(fd, rel=1e-5)

    def test_put_and_call_delta_differ_by_discount_factor(self):
        S, K, r, sigma, T, q = 100, 95, 0.04, 0.25, 0.75, 0.02
        diff = delta.compute_delta(S, K, r, sigma, T, "call", q) - delta.compute_delta(S, K, r, sigma, T, "put", q)
        assert diff == pytest.approx(math.exp(-q * T), abs=1e-12)

    @pytest.mark.parametrize("fn", [lambda: delta.compute_delta(0, 100, 0.05, 0.2, 1),
                                    lambda: gamma.compute_gamma(100, 100, 0.05, 0.0, 1),
                                    lambda: vega.compute_vega(100, 100, 0.05, 0.2, 0)])
    def test_invalid_inputs_return_none(self, fn):
        assert fn() is None


class TestBinomialTree:

    @pytest.mark.parametrize("kind", ["call", "put"])
    def test_european_converges_to_bsm(self, kind):
        tree = crr.calculate(S=100, K=105, r=0.05, sigma=0.25, T=1.0, option_type=kind, steps=800)
        assert tree == pytest.approx(price(100, 105, 0.05, 0.25, 1.0, kind=kind), abs=0.01)

    def test_american_put_is_worth_at_least_the_european_put(self):
        args = dict(S=100, K=110, r=0.08, sigma=0.3, T=1.0, option_type="put", steps=400)
        assert crr.calculate(**args, american=True) > crr.calculate(**args, american=False)

    def test_american_call_without_dividends_equals_european(self):
        args = dict(S=100, K=95, r=0.05, sigma=0.2, T=1.0, option_type="call", steps=400)
        assert crr.calculate(**args, american=True) == pytest.approx(crr.calculate(**args, american=False), abs=1e-9)
