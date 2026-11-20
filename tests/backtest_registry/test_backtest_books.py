"""
Every backtest's book, drilled down: performance, holdings rebuilt from the fills (valued at the latest daily
close), trades, one instrument; and the /research/backtests pages. A fake reader stands for the database (the
reader's SQL is checked against base_infra's engine positions by hand: every book's rebuilt final holdings equal
the engine's position rows).
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from src.application.services.backtest_registry.backtest_book_service import BacktestBookService
from src.application.services.misbuffet.engine.performance_metrics import calculate_performance_metrics


class FakeReader:
    """Book 10 holds sub-portfolios 11 (shares) and 12 (cash)."""

    session = None

    def __init__(self):
        days = [datetime(2026, 6, d, 16) for d in (1, 2, 3, 4, 5)]
        self.values = list(zip(days, [1_000_000, 1_010_000, 1_005_000, 1_020_000, 1_030_000]))
        self._fills = [
            self._fill(1, days[0], "JPM", "BUY", 100, 200.0),
            self._fill(2, days[0], "BAC", "SELL", 300, 40.0),            # a short
            self._fill(3, days[0], "USD", "BUY", 8000, None, asset_type="CurrencyModel", portfolio=12),
            self._fill(4, days[2], "JPM", "SELL", 40, 210.0),
            self._fill(5, days[3], "BAC", "BUY", 300, 38.0),             # short closed
            self._fill(6, days[3], "GS", "BUY", 10, 500.0),
            self._fill(7, days[4], "GS", "BUY", 0, None, status="CANCELLED"),
        ]

    @staticmethod
    def _fill(oid, at, symbol, side, filled, price, asset_type="company_share", portfolio=11, status="FILLED"):
        return {"order_id": oid, "time": at, "portfolio_id": portfolio, "asset_id": {"JPM": 1, "BAC": 2, "GS": 3}
                .get(symbol, 99), "symbol": symbol, "asset_type": asset_type, "side": side, "quantity": filled,
                "filled": filled, "price": price, "status": status}

    def books(self):
        return [{"portfolio_id": 10, "name": "Demo_Portfolio_run7", "values": 5, "first": self.values[0][0],
                 "last": self.values[-1][0]}]

    def sub_portfolios(self, portfolio_id):
        return [{"portfolio_id": 11, "name": "Demo_CS", "type": "CompanySharePortfolio"},
                {"portfolio_id": 12, "name": "Demo_cash", "type": "CurrencyPortfolio"}]

    def fills(self, portfolio_ids, symbol=None):
        return [f for f in self._fills if f["portfolio_id"] in portfolio_ids and (not symbol or f["symbol"] == symbol)]

    def closes(self, asset_ids, start, end):
        # JPM has stored closes (dated at 00:00, with a time zone in the database); BAC / GS have none
        return {1: [(datetime(2026, 6, d), 200.0 + d) for d in (1, 2, 3, 4, 5)]}


@pytest.fixture
def service(monkeypatch):
    s = BacktestBookService(FakeReader())
    monkeypatch.setattr(s, "reader_values", lambda pid: s.reader.values)
    return s


def test_performance_from_the_book_value(service):
    perf = service.performance(10, metrics_fn=calculate_performance_metrics)
    assert [p[1] for p in perf["equity"]][-1] == 1_030_000
    assert min(p[1] for p in perf["drawdown"]) == pytest.approx(1_005_000 / 1_010_000 - 1)
    assert perf["monthly"] == [{"month": "2026-06", "return": pytest.approx(0.03)}]
    assert perf["metrics"]["total_return"] == pytest.approx(0.03)


def test_holdings_are_rebuilt_from_the_fills_and_valued(service):
    at = service.holdings_at(10, "2026-06-02")
    rows = {r["symbol"]: r for r in at["rows"]}
    assert set(rows) == {"JPM", "BAC"}                                    # the cash leg is not a holding
    assert rows["JPM"]["quantity"] == 100 and rows["JPM"]["price"] == 202.0  # the day's stored close
    assert rows["BAC"]["quantity"] == -300 and rows["BAC"]["price"] == 40.0  # no close: last fill price
    assert rows["BAC"]["side"] == "short" and rows["JPM"]["weight"] == pytest.approx(20_200 / 1_010_000)
    last = service.holdings_at(10)
    assert {r["symbol"]: r["quantity"] for r in last["rows"]} == {"JPM": 60, "GS": 10}   # BAC closed
    h = service.holdings(10)
    assert h["symbols"][0] in ("JPM", "BAC") and "GS" in h["symbols"]
    counts = dict((d, v) for d, v in h["positions"])
    assert counts["2026-06-01"] == 2 and counts["2026-06-04"] == 2 and counts["2026-06-05"] == 2
    net = dict(h["exposure"]["net"])
    assert net["2026-06-01"] == pytest.approx(100 * 201 - 300 * 40)


def test_trades_and_one_instrument(service):
    trades = service.trades(10)
    assert trades["total"] == 5 and trades["rows"][0]["order_id"] == 6          # newest first, cash / unfilled out
    assert trades["symbols"] == ["BAC", "GS", "JPM"]
    assert service.trades(10, symbol="JPM")["total"] == 2
    jpm = service.asset(10, "JPM")
    assert [q for _, q in jpm["quantity"]] == [100, 100, 60, 60, 60] and len(jpm["trades"]) == 2


def test_the_backtest_pages(service, monkeypatch):
    from src.interfaces.flask.app import FlaskApp
    fake = SimpleNamespace(books=service)
    app = FlaskApp().get_app()
    app.config.update(RESEARCH_SERVICES_FACTORY=lambda: fake, TESTING=True)
    monkeypatch.setattr("src.application.services.backtest_registry.read_access.close", lambda s: None,
                        raising=False)
    client = app.test_client()
    page = client.get("/research/backtests").get_data(as_text=True)
    assert "Demo_Portfolio_run7" in page and "+3.00%" in page and "not registered" in page
    page = client.get("/research/backtests/10").get_data(as_text=True)
    assert "Holdings on 2026-06-05" in page and "Holding history" in page and "GS" in page
    assert "Holdings on 2026-06-02" in client.get("/research/backtests/10?date=2026-06-02").get_data(as_text=True)
    assert client.get("/research/backtests/10/trades?symbol=JPM").status_code == 200
    assert "Quantity held" in client.get("/research/backtests/10/assets/JPM").get_data(as_text=True)
    assert client.get("/research/backtests/999").status_code == 404
