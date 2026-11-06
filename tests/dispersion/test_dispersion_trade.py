"""Dispersion screener P.04 – P.06: selection, holdings-replicating sizing, the strategy's cost on the broker's
prices, payoff (specification tests 1, 2, 4, 8). Pure domain: no broker, no database."""

from datetime import date, datetime, timedelta, timezone

import pytest

from src.domain.entities.finance.dispersion.dispersion_trade import (
    Leg, etf_price_from, implied_correlation, payoff_at_maturity, premium, raw_positions, replicate,
    reverse_premium, scenarios,
)
from src.domain.entities.finance.dispersion.option_data import (
    Greeks, OptionChain, OptionContractSpec, OptionQuote, Quote,
)
from src.domain.entities.finance.dispersion.option_selection import (
    constituent_expiry, select_atm_strike, select_common_expiry, select_expiry, standard_chain,
)
from src.domain.entities.finance.dispersion.quote_checks import (
    BUY, SELL, freshness_problems, option_liquidity_problems, option_quality_problems,
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

    def test_the_etf_holding_5_shares_of_each_stock_needs_5_calls_on_each(self):     # owner's example
        etf = etf_leg(spot=1000.0)                                         # one ETF share = 5 A + 5 B at 100
        sizing = replicate(etf, [stock("A", 0.5), stock("B", 0.5)], etf_contracts=1)
        assert sizing.positions == pytest.approx({"A": 5.0, "B": 5.0})   # 500 shares of each = 5 calls
        assert sizing.whole_contract_etf_calls == 1

    def test_small_holdings_are_fractions_of_a_contract(self):
        etf = etf_leg(spot=62.0)
        sizing = replicate(etf, [stock("XOM", 0.25, spot=166.0), stock("APA", 0.008, spot=44.5)])
        assert sizing.positions["XOM"] == pytest.approx(100 * 0.25 * 62 / 166 / 100)     # 0.093 contract
        assert sizing.whole_contract_etf_calls == 90                     # 90 ETF calls -> 1 APA call

    def test_different_multipliers(self):                                             # specification test 8
        etf = etf_leg()
        std = replicate(etf, [stock("A", 1.0, multiplier=100)])
        mini = replicate(etf, [stock("A", 1.0, multiplier=10)])
        assert mini.positions["A"] == pytest.approx(10 * std.positions["A"])
        assert mini.long_dollar_delta == pytest.approx(std.long_dollar_delta)

    def test_dollar_delta_is_information_and_may_be_unknown(self):
        etf = etf_leg(delta=0.52)
        sizing = replicate(etf, [stock("A", 0.6, delta=0.55, spot=80.0), stock("B", 0.4, delta=0.40, spot=150.0)])
        assert sizing.relative_net_delta == pytest.approx((0.6 * 0.55 + 0.4 * 0.40) / 0.52 - 1)
        unknown = replicate(etf, [stock("A", 1.0, delta=None)])
        assert unknown.long_dollar_delta is None and unknown.relative_net_delta is None


class TestPremiumAndPayoff:

    def test_cost_is_the_etf_bid_minus_the_constituent_asks(self):
        etf = etf_leg(bid=6.0, ask=6.4)
        legs = [stock("A", 0.5, ask=5.0, bid=4.8), stock("B", 0.5, ask=5.5, bid=5.3)]
        p = premium(etf, legs, replicate(etf, legs))
        assert p.short_proceeds == pytest.approx(600.0)                      # 1 x 100 x bid
        assert p.long_cost == pytest.approx(0.5 * 100 * 5.0 + 0.5 * 100 * 5.5)
        assert p.net_premium == pytest.approx(600 - 525) and p.net_premium_pct == pytest.approx(75 / 600)
        assert p.transaction_cost == pytest.approx(0.2 * 100 + 0.5 * 100 * 0.1 + 0.5 * 100 * 0.1)
        one_sided = premium(etf_leg(bid=6.0, ask=None), legs, replicate(etf, legs))
        assert one_sided.net_premium == pytest.approx(75.0) and one_sided.mid_net_premium is None

    def test_etf_bid_below_constituent_cost_is_negative(self):                       # specification test 4
        etf = etf_leg(bid=4.0)
        legs = [stock("A", 0.5, ask=5.0), stock("B", 0.5, ask=5.0)]
        assert premium(etf, legs, replicate(etf, legs)).net_premium < 0

    def test_basic_convexity(self):                                                  # specification test 1
        etf = etf_leg()
        legs = [stock("A", 0.5), stock("B", 0.5)]
        sizing = replicate(etf, legs)
        prices = {"A": 120.0, "B": 80.0}
        etf_price = etf_price_from(etf, legs, prices)
        assert etf_price == pytest.approx(100.0)
        pay = payoff_at_maturity(etf, legs, sizing, etf_price, prices)
        assert pay.long_basket > 0 and pay.short_etf == 0 and pay.combined > 0

    def test_perfectly_correlated_stocks(self):                                      # specification test 2
        etf = etf_leg()
        legs = [stock("A", 0.3, spot=50.0, strike=50.0), stock("B", 0.7, spot=200.0, strike=200.0)]
        sizing = replicate(etf, legs)
        for move in (0.8, 1.0, 1.1, 1.3):
            prices = {"A": 50.0 * move, "B": 200.0 * move}
            pay = payoff_at_maturity(etf, legs, sizing, etf_price_from(etf, legs, prices), prices)
            assert pay.combined == pytest.approx(0.0, abs=1e-9)

    def test_diagnostics(self):
        legs = [stock("A", 0.5, bid=4.9, ask=5.1, implied_vol=0.25), stock("B", 0.5, bid=4.9, ask=5.1, implied_vol=0.25)]
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
        assert option_quality_problems(self.option(), self.NOW, CONFIG, SELL) == []
        assert option_quality_problems(self.option(bid=0), self.NOW, CONFIG, SELL) == ["no bid (bid 0)"]
        assert option_quality_problems(self.option(bid=0), self.NOW, CONFIG, BUY) == []        # the ask is the price
        assert option_quality_problems(self.option(ask=None), self.NOW, CONFIG, BUY) == ["no ask (ask None)"]
        assert option_quality_problems(self.option(delta=None), self.NOW, CONFIG, BUY) == []   # greeks: information
        assert any("frozen" in p for p in option_quality_problems(self.option(mdt=2), self.NOW, CONFIG, BUY))
        assert any("old" in p for p in option_quality_problems(self.option(age=600), self.NOW, CONFIG, BUY))
        assert freshness_problems(Quote(), self.NOW, CONFIG) == ["no quote time"]

    def test_no_spread_limit_only_the_optional_minimums(self):                       # specification test 7
        wide = self.option(bid=1.0, ask=3.0)                                          # 100 % spread
        assert option_liquidity_problems(wide, CONFIG, is_etf=False) == []
        assert option_liquidity_problems(wide, CONFIG, is_etf=True) == []
        strict = DispersionScreenConfig(min_stock_open_interest=100)
        assert "open interest None < 100" in option_liquidity_problems(self.option(), strict, is_etf=False)


def test_scenarios_show_the_dispersion_effect():
    etf = etf_leg()
    legs = [stock("A", 0.5), stock("B", 0.3, spot=50.0, strike=50.0), stock("C", 0.2, spot=20.0, strike=20.0)]
    sizing = replicate(etf, legs)
    by_name = {s["scenario"]: s for s in scenarios(etf, legs, sizing, net_premium=-100.0)}
    for m in ("-10%", "+0%", "+10%"):
        market, disp = by_name[f"market {m}"], by_name[f"dispersion {m}"]
        assert market["etf_price"] == pytest.approx(disp["etf_price"])            # same average move
        assert disp["combined"] >= market["combined"] - 1e-9                       # dispersion helps the long calls
        assert market["combined"] == pytest.approx(0.0, abs=1e-9)                  # no dispersion: offset
    assert by_name["dispersion +0%"]["combined"] > 0 and by_name["market +0%"]["pnl"] == pytest.approx(-100.0)


def test_reversed_strategy_buys_the_etf_call_at_the_ask_and_sells_the_constituent_calls_at_the_bid():
    etf = etf_leg(bid=6.0, ask=6.4)
    legs = [stock("A", 0.5, bid=4.8, ask=5.0), stock("B", 0.5, bid=5.3, ask=5.5)]
    r = reverse_premium(etf, legs, replicate(etf, legs))
    assert r.etf_call_cost == pytest.approx(640.0)                                 # 1 x 100 x ETF ask
    assert r.constituent_proceeds == pytest.approx(0.5 * 100 * 4.8 + 0.5 * 100 * 5.3)
    assert r.net_premium == pytest.approx(505.0 - 640.0) and r.net_premium_pct == pytest.approx(-135.0 / 640.0)
    assert reverse_premium(etf_leg(ask=None), legs, replicate(etf, legs)) is None
    assert reverse_premium(etf, [stock("A", 0.5, bid=None), legs[1]], replicate(etf, legs)) is None


def test_implied_correlation_on_each_sides_prices():
    legs = [stock("A", 0.5, implied_vol=0.30, ask_implied_vol=0.25, bid_implied_vol=0.20),
            stock("B", 0.5, implied_vol=0.30, ask_implied_vol=0.25, bid_implied_vol=0.20)]
    own = 2 * (0.5 * 0.25) ** 2
    assert implied_correlation(0.18, legs, vol="ask_implied_vol") == pytest.approx((0.0324 - own) / own)
    own_bid = 2 * (0.5 * 0.20) ** 2
    assert implied_correlation(0.19, legs, vol="bid_implied_vol") == pytest.approx((0.0361 - own_bid) / own_bid)
    assert implied_correlation(0.18, [legs[0], stock("B", 0.5)], vol="ask_implied_vol") is None


def test_the_broker_bid_and_ask_volatilities_are_read():
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_option_market_data import greeks_from
    ticks = {13: {'implied_vol': 0.21, 'delta': 0.5}, 10: {'implied_vol': 0.20}, 11: {'implied_vol': 0.22}}
    g = greeks_from(ticks)
    assert (g.implied_vol, g.bid_implied_vol, g.ask_implied_vol) == (0.21, 0.20, 0.22)
    delayed = greeks_from({83: {'implied_vol': 0.21}, 80: {'implied_vol': -1}, 81: {'implied_vol': 0.23}})
    assert delayed.bid_implied_vol is None and delayed.ask_implied_vol == 0.23          # -1: not computed
