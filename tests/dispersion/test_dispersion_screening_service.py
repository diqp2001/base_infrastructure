"""Dispersion screener P.07: the screening service on a fake OptionMarketDataPort (no broker). Opportunity,
premium rejection (spec test 4), option coverage (spec test 6), illiquid constituent (spec test 7), frozen quotes."""

from datetime import date, datetime, timedelta, timezone

import pytest

from src.application.services.dispersion.dispersion_screening_service import (
    DATA_UNAVAILABLE, MAX_CONSECUTIVE_UNAVAILABLE, OPPORTUNITY, DispersionScreeningService,
)
from src.domain.entities.finance.dispersion.etf_holdings import ConstituentWeights
from src.domain.entities.finance.dispersion.option_data import (
    Greeks, OptionChain, OptionQuote, Quote, Underlying, UnderlyingQuote,
)
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable, OptionMarketDataPort

DAY = date(2026, 11, 5)
NOW = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc)
EXPIRY = DAY + timedelta(days=29)


class FakeMarket(OptionMarketDataPort):
    """spots: symbol -> price; option: symbol -> (bid, ask, delta); no_options / missing: symbols."""

    def __init__(self, spots, options, no_options=(), missing=(), mdt=1):
        self.spots, self.options, self.no_options, self.missing, self.mdt = spots, options, set(no_options), set(missing), mdt

    def resolve_underlyings(self, symbols, screening_date):
        return {s: None if s in self.missing else Underlying(s, hash(s) % 10_000, "STK", "USD", "NYSE",
                                                             "ETF" if s == "ETF" else "COMMON") for s in symbols}

    def option_chains(self, underlying, screening_date):
        if underlying.symbol in self.no_options:
            return []
        spot = self.spots[underlying.symbol]
        strikes = tuple(round(spot * k, 2) for k in (0.9, 0.95, 1.0, 1.05, 1.1))
        return [OptionChain(underlying.symbol, underlying.symbol, 100.0, (DAY + timedelta(days=8), EXPIRY), strikes)]

    def listed_strikes(self, chain, expiry, right, screening_date):
        return chain.strikes

    def underlying_quotes(self, underlyings, screening_date):
        return {u.symbol: UnderlyingQuote(u, Quote(bid=self.spots[u.symbol] - 0.01, ask=self.spots[u.symbol] + 0.01,
                                                   quote_time=NOW, market_data_type=1)) for u in underlyings}

    def option_quotes(self, contracts, screening_date):
        out = {}
        for spec in contracts:
            bid, ask, delta = self.options[spec.underlying]
            out[spec.key] = OptionQuote(spec, Quote(bid=bid, ask=ask, quote_time=NOW - timedelta(seconds=3),
                                                    market_data_type=self.mdt),
                                        Greeks(implied_vol=0.2, delta=delta, gamma=0.05, vega=0.1, theta=-0.05))
        return out


def weights(**w):
    return ConstituentWeights("ETF", DAY, dict(w), 1.0, [], "test")


def screen(market, config=DispersionScreenConfig(), **w):
    service = DispersionScreeningService(market, config, now=lambda: NOW)
    return service.screen([("ETF", "Test ETF", weights(**w))], DAY)[0]


SPOTS = {"ETF": 100.0, "A": 50.0, "B": 200.0}


def test_opportunity_when_the_etf_bid_pays_for_the_basket():
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.20, 1.25, 0.5), "B": (4.80, 5.0, 0.5)})
    c = screen(market, A=0.5, B=0.5)
    assert c.status == OPPORTUNITY and c.reasons == []
    assert c.expiry == EXPIRY and c.dte == 29 and c.coverage == 1.0
    # one ETF call = 100 ETF shares = 50 A shares (1 A call) + 12.5 B shares (0.25 B call): the holdings
    assert c.sizing.etf_contracts == 1 and c.sizing.positions == pytest.approx({"A": 1.0, "B": 0.25})
    assert c.premium.short_proceeds == pytest.approx(500.0)                      # 100 x ETF bid 5.00
    assert c.premium.long_cost == pytest.approx(1.0 * 100 * 1.25 + 0.25 * 100 * 5.0)   # at the asks
    assert c.premium.net_premium == pytest.approx(250.0) and c.sizing.whole_contract_etf_calls == 4
    # reversed: ETF call bought at its ask 5.10, constituent calls sold at their bids
    assert c.reverse.net_premium == pytest.approx(1.0 * 100 * 1.20 + 0.25 * 100 * 4.80 - 510.0)
    a = next(r for r in c.constituents if r.symbol == "A")
    assert a.contracts == c.sizing.positions["A"] and a.call_cost == pytest.approx(a.contracts * 100 * 1.25)


def test_premium_rejection():                                                        # specification test 4
    market = FakeMarket(SPOTS, {"ETF": (3.0, 3.1, 0.5), "A": (1.6, 1.65, 0.5), "B": (6.4, 6.6, 0.5)})
    c = screen(market, A=0.5, B=0.5)
    assert c.status == "rejected" and "net premium" in c.reasons[-1] and c.premium.net_premium < 0


def test_missing_options_below_coverage():                                          # specification test 6
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)},
                        no_options=["B"])
    c = screen(market, A=0.5, B=0.5)
    assert c.status == "not screenable" and c.reasons[-1] == ("option coverage below 100%: 1 of 2 constituents "
                                                             "unusable (B: no listed options)")
    assert next(r for r in c.constituents if r.symbol == "B").status == "no listed options"
    relaxed = screen(market, DispersionScreenConfig(min_option_coverage=0.5), A=0.5, B=0.5)
    assert relaxed.coverage == 0.5 and any("renormalised" in r for r in relaxed.reasons)


def test_the_etf_call_needs_a_bid_and_every_constituent_call_an_ask():
    # wide spreads and one-sided quotes on the other side are fine (owner, 2026-11-06)
    one_sided = FakeMarket(SPOTS, {"ETF": (5.0, None, 0.5), "A": (None, 1.25, 0.5), "B": (1.0, 5.0, 0.5)})
    c = screen(one_sided, A=0.5, B=0.5)
    assert c.status == OPPORTUNITY and c.premium.mid_net_premium is None
    no_bid = screen(FakeMarket(SPOTS, {"ETF": (None, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)}),
                    A=0.5, B=0.5)
    assert no_bid.status == "not screenable" and no_bid.reasons == ["ETF call: no bid (bid None)"]
    no_ask = screen(FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, None, 0.5), "B": (4.8, 5.0, 0.5)}),
                    A=0.5, B=0.5)
    assert no_ask.status == "not screenable" and "A: no ask (ask None)" in no_ask.reasons[-1]


def test_volume_minimum_rejects_the_etf():                                          # specification test 7
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    c = screen(market, DispersionScreenConfig(min_stock_option_volume=10), A=0.5, B=0.5)
    assert c.status == "rejected" and "volume / open interest minimums: A, B" in c.reasons[0]


def test_frozen_quotes_are_not_mixed_with_live_ones():
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)}, mdt=2)
    c = screen(market, A=0.5, B=0.5)
    assert c.status == "not screenable" and "frozen" in c.reasons[0]


def test_unknown_share_and_ranking():
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)}, missing=["B"])
    c = screen(market, A=0.5, B=0.5)
    assert next(r for r in c.constituents if r.symbol == "B").status == "not a US-listed share at the broker"
    good = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    service = DispersionScreeningService(good, DispersionScreenConfig(), now=lambda: NOW)
    ranked = service.screen([("BAD", "x", weights(A=0.5, B=0.5)), ("ETF", "y", weights(A=0.5, B=0.5))], DAY)
    assert ranked[0].etf == "ETF" and ranked[0].status == OPPORTUNITY


def test_project_writes_the_ranked_candidates(tmp_path):
    import json
    from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
        write_candidates,
    )
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    c = screen(market, A=0.5, B=0.5)
    write_candidates(str(tmp_path), [c])
    saved = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))[0]
    assert saved["status"] == OPPORTUNITY and saved["etf_strike"] == 100.0 and saved["net_premium"] >= 0
    assert [leg["ticker"] for leg in saved["constituent_legs"]] == ["A", "B"]
    assert (tmp_path / "candidates.csv").read_text(encoding="utf-8").startswith("etf,name,status")


def test_results_pages(tmp_path, monkeypatch):
    from flask import Flask
    from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
        write_candidates,
    )
    from src.interfaces.flask.web.controllers import dispersion_controller
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    write_candidates(str(tmp_path / "2026-11-05"), [screen(market, A=0.5, B=0.5)])
    monkeypatch.setattr(dispersion_controller, "RESULTS_DIR", str(tmp_path))
    app = Flask(__name__, template_folder="../../src/interfaces/flask/web/templates")
    app.register_blueprint(dispersion_controller.dispersion_bp)
    client = app.test_client()
    page = client.get("/dispersion/")
    assert page.status_code == 200 and b"opportunity" in page.data and b"2026-11-05" in page.data
    detail = client.get("/dispersion/etf/ETF?date=2026-11-05")
    assert detail.status_code == 200 and b"Constituents" in detail.data and b"Net premium" in detail.data
    assert client.get("/dispersion/api/candidates").get_json()["candidates"][0]["etf"] == "ETF"
    assert client.get("/dispersion/etf/NOPE").status_code == 404
    assert client.get("/dispersion/?date=../../etc").status_code == 404
    # a file written before newer fields existed (e.g. the reversed strategy) still renders
    import json
    rows = json.loads((tmp_path / "2026-11-05" / "candidates.json").read_text(encoding="utf-8"))
    for row in rows:
        for key in [k for k in row if k.startswith(("reverse_", "implied_correlation_etf_"))]:
            del row[key]
        for leg in row["constituent_legs"]:
            leg.pop("bid_iv"), leg.pop("ask_iv")
    (tmp_path / "2026-11-04").mkdir()
    (tmp_path / "2026-11-04" / "candidates.json").write_text(json.dumps(rows), encoding="utf-8")
    assert client.get("/dispersion/?date=2026-11-04").status_code == 200
    assert client.get("/dispersion/etf/ETF?date=2026-11-04").status_code == 200


def test_the_expiry_is_the_one_the_constituents_list():
    class WeeklyEtf(FakeMarket):
        def option_chains(self, underlying, screening_date):
            chain = super().option_chains(underlying, screening_date)
            if underlying.symbol != "ETF":
                return chain
            weekly = EXPIRY - timedelta(days=7)                       # nearer 30 DTE, listed by the ETF only
            return [OptionChain("ETF", "ETF", 100.0, (weekly, EXPIRY), chain[0].strikes)]
    market = WeeklyEtf(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    c = screen(market, A=0.5, B=0.5)
    assert c.expiry == EXPIRY and c.coverage == 1.0


def test_a_silent_source_is_data_unavailable_not_not_found():
    class Silent(FakeMarket):
        calls = 0

        def resolve_underlyings(self, symbols, screening_date):
            Silent.calls += 1
            raise MarketDataUnavailable("IBKR did not answer the ETF contract details request within 15 s")
    service = DispersionScreeningService(Silent(SPOTS, {}), DispersionScreenConfig(), now=lambda: NOW)
    etfs = [(f"E{i}", "Test", weights(A=0.5, B=0.5)) for i in range(5)]
    out = service.screen(etfs, DAY)
    assert [c.status for c in out] == [DATA_UNAVAILABLE] * 5
    assert Silent.calls == MAX_CONSECUTIVE_UNAVAILABLE            # then the screen stops asking
    assert not any("not found" in r for c in out for r in c.reasons)


def test_the_ibkr_adapter_raises_when_the_gateway_does_not_answer():
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_option_market_data import (
        IBKROptionMarketData,
    )

    class SilentClient:
        contract_details, contract_details_done, request_errors = {}, set(), {}

        def request_contract_details(self, req_id, contract):
            pass
    md = IBKROptionMarketData(SilentClient(), today=lambda: DAY, lookup_timeout_seconds=0.05, poll_seconds=0.01)
    with pytest.raises(MarketDataUnavailable):
        md.resolve_underlyings(["XLE"], DAY)


def test_lookups_are_reused_so_a_second_run_asks_for_quotes_only():
    import json

    class Counting(FakeMarket):
        lookups = 0

        def resolve_underlyings(self, symbols, screening_date):
            Counting.lookups += 1
            return super().resolve_underlyings(symbols, screening_date)

        def option_chains(self, underlying, screening_date):
            Counting.lookups += 1
            return super().option_chains(underlying, screening_date)

        def listed_strikes(self, chain, expiry, right, screening_date):
            Counting.lookups += 1
            return super().listed_strikes(chain, expiry, right, screening_date)
    quotes = {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)}
    first = DispersionScreeningService(Counting(SPOTS, quotes), DispersionScreenConfig(), now=lambda: NOW)
    a = first.screen([("ETF", "Test ETF", weights(A=0.5, B=0.5))], DAY)[0]
    saved = json.loads(json.dumps(first.export_lookups(DAY)))
    Counting.lookups = 0
    second = DispersionScreeningService(Counting(SPOTS, quotes), DispersionScreenConfig(), now=lambda: NOW)
    assert second.import_lookups(saved, DAY) and not second.import_lookups(saved, DAY + timedelta(days=1))
    b = second.screen([("ETF", "Test ETF", weights(A=0.5, B=0.5))], DAY)[0]
    assert Counting.lookups == 0 and b.status == a.status == OPPORTUNITY and b.expiry == a.expiry


def test_lookups_stop_at_the_first_unusable_constituent():
    asked = []

    class Recording(FakeMarket):
        def resolve_underlyings(self, symbols, screening_date):
            asked.extend(symbols)
            return super().resolve_underlyings(symbols, screening_date)
    spots = {"ETF": 100.0, **{s: 50.0 for s in "ABCDE"}}
    market = Recording(spots, {s: (1.2, 1.25, 0.5) for s in spots}, missing=["B"])
    c = screen(market, A=0.2, B=0.2, C=0.2, D=0.2, E=0.2)
    assert asked == ["ETF", "A", "B"]                              # C, D, E never sent to the broker
    assert [r.status for r in c.constituents][2:] == ["not checked"] * 3
    assert "3 not checked" in c.reasons[-1]
    asked.clear()
    relaxed = screen(market, DispersionScreenConfig(min_option_coverage=0.8), A=0.2, B=0.2, C=0.2, D=0.2, E=0.2)
    assert asked == ["ETF", "A", "B", "C", "D", "E"] and relaxed.coverage == 0.8   # 1 of 5 allowed at 80 %


def test_price_age_is_judged_when_the_quotes_arrive_not_after_the_lookups():
    clock = iter(NOW + timedelta(seconds=40 * i) for i in range(1000))     # 40 s pass between two reads of the clock
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})

    class LateQuotes(FakeMarket):                                          # quotes stamped as they are served
        def underlying_quotes(self, underlyings, screening_date):
            t = next(clock)
            return {u.symbol: UnderlyingQuote(u, Quote(bid=self.spots[u.symbol] - 0.01,
                                                       ask=self.spots[u.symbol] + 0.01, quote_time=t,
                                                       market_data_type=1)) for u in underlyings}

        def option_quotes(self, contracts, screening_date):
            t = next(clock)
            out = super().option_quotes(contracts, screening_date)
            return {k: OptionQuote(q.contract, Quote(bid=q.quote.bid, ask=q.quote.ask, quote_time=t,
                                                     market_data_type=1), q.greeks) for k, q in out.items()}
    late = LateQuotes(market.spots, market.options)
    service = DispersionScreeningService(late, DispersionScreenConfig(), now=lambda: next(clock))
    c = service.screen([("ETF", "Test ETF", weights(A=0.5, B=0.5))], DAY)[0]
    assert c.status == OPPORTUNITY, c.reasons
