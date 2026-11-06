"""Dispersion screener P.04 – P.06: selection, dollar-delta-neutral sizing, premium, payoff (specification tests 1,
2, 3, 4, 7, 8). Pure domain: no broker, no database."""

from datetime import date, datetime, timedelta, timezone

import pytest

from src.domain.entities.finance.dispersion.dispersion_trade import (
    Leg, etf_price_from, implied_correlation, payoff_at_maturity, premium, raw_positions, scenarios, size_fractional,
    size_whole_contracts, weighted_comparison,
)
from src.domain.entities.finance.dispersion.option_data import (
    Greeks, OptionChain, OptionContractSpec, OptionQuote, Quote,
)
from src.domain.entities.finance.dispersion.option_selection import (
    constituent_expiry, select_atm_strike, select_common_expiry, select_expiry, standard_chain,
)
from src.domain.entities.finance.dispersion.quote_checks import (
    freshness_problems, option_liquidity_problems, option_quality_problems,
)
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig

CONFIG = DispersionScreenConfig()
DAY = date(2026, 11, 5)


def etf_leg(**kw):
    base = dict(symbol="ETF", spot=100.0, strike=100.0, multiplier=100, delta=0.5, bid=4.0, ask=4.2)
    base.update(kw)
    return Leg(**base)


def stock(symbol, weight, **kw):
    base = dict(symbol=symbol, spot=100.0, strike=100.0, multiplier=100, delta=0.5, bid=5.0, ask=5.2, weight=weight)
    base.update(kw)
    return Leg(**base)


class TestSelection:

    def test_expiry_nearest_target_inside_the_window(self):
        expiries = [DAY + timedelta(days=d) for d in (1, 15, 22, 36, 50, 80)]
        assert select_expiry(expiries, DAY, CONFIG) == DAY + timedelta(days=36)        # |36-30| < |22-30|
        assert select_expiry([DAY + timedelta(days=d) for d in (1, 70)], DAY, CONFIG) is None

    def test_common_expiry_prefers_what_the_constituents_list(self):
        weekly, monthly = DAY + timedelta(days=29), DAY + timedelta(days=43)
        stocks = [[monthly], [monthly], [weekly, monthly]]
        assert select_common_expiry([weekly, monthly], stocks, DAY, CONFIG) == monthly
        assert select_common_expiry([weekly, monthly], [[weekly, monthly]], DAY, CONFIG) == weekly   # tie -> nearest 30

    def test_constituent_expiry_exception_is_explicit(self):
        etf_expiry = DAY + timedelta(days=29)
        assert constituent_expiry([etf_expiry], etf_expiry, DAY, CONFIG).expiry == etf_expiry
        missing = constituent_expiry([DAY + timedelta(days=31)], etf_expiry, DAY, CONFIG)
        assert missing.expiry is None and "same expiration required" in missing.exception
        relaxed = DispersionScreenConfig(require_same_expiration=False)
        other = constituent_expiry([DAY + timedelta(days=31)], etf_expiry, DAY, relaxed)
        assert other.expiry == DAY + timedelta(days=31) and "instead of" in other.exception

    def test_atm_strike_and_standard_class(self):
        assert select_atm_strike([40, 42.5, 45], 43.3) == 42.5
        assert select_atm_strike([42, 44], 43.0) == 42                                    # tie -> lower strike
        std = OptionChain("X", "X", 100.0, (DAY,), (1.0,))
        adjusted = OptionChain("X", "X1", 112.0, (DAY,), (1.0,))
        chosen, notes = standard_chain([adjusted, std])
        assert chosen is std and notes == ["trading class X1 x112 not used"]
        assert standard_chain([])[0] is None


class TestSizing:

    def test_raw_positions_follow_value_weights_not_share_counts(self):
        etf = etf_leg(spot=50.0)
        legs = [stock("A", 0.5, spot=200.0), stock("B", 0.5, spot=25.0)]
        raw = raw_positions(etf, legs)
        # one ETF call = 100 ETF shares = 5000 USD: 2500 USD of A (12.5 sh) and of B (100 sh)
        assert raw == pytest.approx({"A": 12.5 / 100, "B": 100 / 100})

    def test_delta_neutral_with_actual_deltas(self):                                 # specification test 3
        etf = etf_leg(delta=0.52)
        legs = [stock("A", 0.6, delta=0.55, spot=80.0), stock("B", 0.4, delta=0.40, spot=150.0)]
        frac = size_fractional(etf, legs)
        assert abs(frac.relative_net_delta) < 1e-12
        whole = size_whole_contracts(etf, legs, CONFIG)
        assert all(float(q).is_integer() and q >= 1 for q in whole.positions.values())
        assert abs(whole.relative_net_delta) <= CONFIG.delta_tolerance

    def test_different_multipliers(self):                                             # specification test 8
        etf = etf_leg()
        std = size_fractional(etf, [stock("A", 1.0, multiplier=100)])
        mini = size_fractional(etf, [stock("A", 1.0, multiplier=10)])
        assert mini.positions["A"] == pytest.approx(10 * std.positions["A"])
        assert mini.long_dollar_delta == pytest.approx(std.long_dollar_delta) == pytest.approx(std.short_dollar_delta)

    def test_whole_contracts_report_when_no_n_fits(self):
        etf = etf_leg()
        legs = [stock("A", 0.999, spot=100.0), stock("B", 0.001, spot=100.0)]        # B rounds to 0 below N=5
        sizing = size_whole_contracts(etf, legs, DispersionScreenConfig(max_etf_contracts=3))
        assert sizing.zero_positions == ["B"]


class TestPremiumAndPayoff:

    def test_premium_on_executable_prices(self):
        etf = etf_leg(bid=6.0, ask=6.4)
        legs = [stock("A", 0.5, ask=5.0, bid=4.8), stock("B", 0.5, ask=5.5, bid=5.3)]
        sizing = size_fractional(etf, legs)
        p = premium(etf, legs, sizing)
        assert p.short_proceeds == pytest.approx(600.0)                      # 1 x 100 x bid
        assert p.long_cost == pytest.approx(0.5 * 100 * 5.0 + 0.5 * 100 * 5.5)
        assert p.net_premium == pytest.approx(600 - 525) and p.net_premium_pct == pytest.approx(75 / 600)
        assert p.transaction_cost == pytest.approx(0.2 * 100 + 0.5 * 100 * 0.1 + 0.5 * 100 * 0.1)

    def test_etf_bid_below_constituent_cost_is_negative(self):                       # specification test 4
        etf = etf_leg(bid=4.0)
        legs = [stock("A", 0.5, ask=5.0), stock("B", 0.5, ask=5.0)]
        assert premium(etf, legs, size_fractional(etf, legs)).net_premium < 0

    def test_basic_convexity(self):                                                  # specification test 1
        etf = etf_leg()
        legs = [stock("A", 0.5), stock("B", 0.5)]
        sizing = size_fractional(etf, legs)
        prices = {"A": 120.0, "B": 80.0}
        etf_price = etf_price_from(etf, legs, prices)
        assert etf_price == pytest.approx(100.0)
        pay = payoff_at_maturity(etf, legs, sizing, etf_price, prices)
        assert pay.long_basket > 0 and pay.short_etf == 0 and pay.combined > 0

    def test_perfectly_correlated_stocks(self):                                      # specification test 2
        etf = etf_leg()
        legs = [stock("A", 0.3, spot=50.0, strike=50.0), stock("B", 0.7, spot=200.0, strike=200.0)]
        sizing = size_fractional(etf, legs)
        for move in (0.8, 1.0, 1.1, 1.3):
            prices = {"A": 50.0 * move, "B": 200.0 * move}
            pay = payoff_at_maturity(etf, legs, sizing, etf_price_from(etf, legs, prices), prices)
            assert pay.combined == pytest.approx(0.0, abs=1e-9)

    def test_diagnostics(self):
        etf = etf_leg(bid=3.9, ask=4.1, implied_vol=0.18)
        legs = [stock("A", 0.5, bid=4.9, ask=5.1, implied_vol=0.25), stock("B", 0.5, bid=4.9, ask=5.1, implied_vol=0.25)]
        w = weighted_comparison(etf, legs)
        assert w.weighted_constituent_call_value == pytest.approx(5.0) and w.dispersion_premium == pytest.approx(-1.0)
        rho = implied_correlation(0.18, legs)
        # 0.18^2 = 2 x 0.25^2 x 0.25^2... : (0.0324 - 0.03125) / (0.0625 - 0.03125)
        assert rho == pytest.approx((0.0324 - 0.03125) / 0.03125)
        assert implied_correlation(0.18, [legs[0], stock("B", 0.5)]) is None


class TestQuoteChecks:
    NOW = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc)

    def option(self, bid=1.0, ask=1.04, delta=0.5, mdt=1, age=5, volume=10.0, oi=None):
        spec = OptionContractSpec("X", DAY, 10.0, "C", 100, "X")
        q = Quote(bid=bid, ask=ask, volume=volume, quote_time=self.NOW - timedelta(seconds=age), market_data_type=mdt)
        return OptionQuote(spec, q, Greeks(delta=delta), open_interest=oi)

    def test_quality(self):
        assert option_quality_problems(self.option(), self.NOW, CONFIG) == []
        assert any("two-sided" in p for p in option_quality_problems(self.option(bid=0), self.NOW, CONFIG))
        assert any("frozen" in p for p in option_quality_problems(self.option(mdt=2), self.NOW, CONFIG))
        assert any("old" in p for p in option_quality_problems(self.option(age=600), self.NOW, CONFIG))
        assert any("delta" in p for p in option_quality_problems(self.option(delta=None), self.NOW, CONFIG))
        assert freshness_problems(Quote(), self.NOW, CONFIG) == ["no quote time"]

    def test_illiquid_constituent(self):                                             # specification test 7
        wide = self.option(bid=1.0, ask=1.3)                                          # 26 % spread
        assert option_liquidity_problems(wide, CONFIG, is_etf=False)
        assert option_liquidity_problems(self.option(bid=1.0, ask=1.08), CONFIG, is_etf=True)   # > 5 % for the ETF
        assert option_liquidity_problems(self.option(bid=1.0, ask=1.08), CONFIG, is_etf=False) == []
        strict = DispersionScreenConfig(min_stock_open_interest=100)
        assert "open interest None < 100" in option_liquidity_problems(self.option(), strict, is_etf=False)


def test_scenarios_show_the_dispersion_effect():
    etf = etf_leg()
    legs = [stock("A", 0.5), stock("B", 0.3, spot=50.0, strike=50.0), stock("C", 0.2, spot=20.0, strike=20.0)]
    sizing = size_fractional(etf, legs)
    by_name = {s["scenario"]: s for s in scenarios(etf, legs, sizing, net_premium=-100.0)}
    for m in ("-10%", "+0%", "+10%"):
        market, disp = by_name[f"market {m}"], by_name[f"dispersion {m}"]
        assert market["etf_price"] == pytest.approx(disp["etf_price"])            # same average move
        assert disp["combined"] >= market["combined"] - 1e-9                       # dispersion helps the long calls
        assert market["combined"] == pytest.approx(0.0, abs=1e-9)                  # no dispersion: offset
    assert by_name["dispersion +0%"]["combined"] > 0 and by_name["market +0%"]["pnl"] == pytest.approx(-100.0)
