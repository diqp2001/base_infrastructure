"""Dispersion screener: the per-ETF maturities view (every expiry the ETF and all its constituents list), its job
module and its page. Fake market data, temp results folder; no broker, no Docker."""

import json
from datetime import date, datetime, timedelta, timezone

from src.domain.entities.finance.dispersion.option_selection import common_expiries
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from tests.dispersion.test_dispersion_screening_service import DAY, EXPIRY, NOW, SPOTS, FakeMarket, weights

QUOTES = {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)}
WEEKLY = DAY + timedelta(days=8)             # FakeMarket lists (WEEKLY, EXPIRY) for every underlying


def test_common_expiries_are_listed_by_the_etf_and_every_constituent():
    d = date(2026, 11, 6)
    etf = [d + timedelta(days=n) for n in (3, 14, 42, 133, 500)]
    stocks = [[d + timedelta(days=n) for n in (14, 42, 133)], [d + timedelta(days=n) for n in (14, 42)]]
    assert common_expiries(etf, stocks, d, 1, 400) == [d + timedelta(days=14), d + timedelta(days=42)]
    assert common_expiries(etf, stocks, d, 20, 400) == [d + timedelta(days=42)]


def test_the_service_prices_every_common_expiry():
    from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
    service = DispersionScreeningService(FakeMarket(SPOTS, QUOTES), DispersionScreenConfig(), now=lambda: NOW)
    out, reasons = service.maturities("ETF", "Test ETF", weights(A=0.5, B=0.5), DAY)
    assert reasons == [] and [c.expiry for c in out] == [WEEKLY, EXPIRY]
    assert all(c.premium is not None for c in out) and out[0].dte == 8
    none, why = DispersionScreeningService(FakeMarket(SPOTS, QUOTES, no_options=["B"]), DispersionScreenConfig(),
                                           now=lambda: NOW).maturities("ETF", "x", weights(A=0.5, B=0.5), DAY)
    assert none == [] and why == ["B: no listed options"]


def _results_dir(tmp_path):
    day = tmp_path / DAY.isoformat()
    day.mkdir()
    (day / "universe.json").write_text(json.dumps({"etfs": [{
        "ticker": "ETF", "name": "Test ETF", "status": "eligible", "holdings_as_of": DAY.isoformat(),
        "weights": {"A": 0.5, "B": 0.5}, "equity_share": 1.0, "holdings_source": "test"}]}), encoding="utf-8")
    return str(tmp_path)


def test_the_job_writes_every_maturity_and_its_status(tmp_path):
    from src.application.managers.project_managers.etf_dispersion_screener_project import maturities
    results = _results_dir(tmp_path)
    in_hours = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc)                      # 10:00 New York
    result = maturities.run("ETF", DAY.isoformat(), market_data=FakeMarket(SPOTS, QUOTES),
                            config={"results_dir": results}, now=lambda: in_hours)
    assert [m["expiry"] for m in result["maturities"]] == [str(WEEKLY), str(EXPIRY)] and not result["frozen_quotes"]
    saved = json.loads((tmp_path / DAY.isoformat() / "maturities" / "ETF.json").read_text(encoding="utf-8"))
    assert saved["maturities"][1]["net_premium"] is not None and saved["maturities"][1]["constituent_legs"]
    assert maturities.read_status(results, DAY.isoformat(), "ETF")["state"] == "done"
    assert all(m["complete"] for m in result["maturities"])


def test_only_maturities_with_every_bid_and_ask_are_complete(tmp_path):
    from src.application.managers.project_managers.etf_dispersion_screener_project import maturities
    no_bid = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (None, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    result = maturities.run("ETF", DAY.isoformat(), market_data=no_bid, config={"results_dir": _results_dir(tmp_path)},
                            now=lambda: datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc))
    # priced (A has an ask) but A's call has no bid: the reversed strategy is missing -> not complete
    assert [m["net_premium"] is not None for m in result["maturities"]] == [True, True]
    assert [m["complete"] for m in result["maturities"]] == [False, False]


def test_after_the_close_the_job_labels_frozen_quotes(tmp_path):
    from src.application.managers.project_managers.etf_dispersion_screener_project import maturities
    assert maturities.market_open(datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc))         # Friday 10:00 ET
    assert not maturities.market_open(datetime(2026, 11, 6, 21, 30, tzinfo=timezone.utc))    # Friday 16:30 ET
    assert not maturities.market_open(datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc))     # Saturday


def test_the_page_starts_one_job_at_a_time(tmp_path, monkeypatch):
    from flask import Flask
    from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
        write_candidates,
    )
    from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
    from src.interfaces.flask.web.controllers import dispersion_controller
    results = _results_dir(tmp_path)
    service = DispersionScreeningService(FakeMarket(SPOTS, QUOTES), DispersionScreenConfig(), now=lambda: NOW)
    write_candidates(str(tmp_path / DAY.isoformat()), service.screen([("ETF", "Test ETF", weights(A=0.5, B=0.5))], DAY))
    monkeypatch.setattr(dispersion_controller, "RESULTS_DIR", results)
    launched = []
    monkeypatch.setattr(dispersion_controller, "_launch", lambda ticker, day: launched.append((ticker, day)))
    app = Flask(__name__, template_folder="../../src/interfaces/flask/web/templates")
    app.register_blueprint(dispersion_controller.dispersion_bp)
    client = app.test_client()
    day = DAY.isoformat()
    page = client.get(f"/dispersion/etf/ETF/maturities?date={day}")
    assert page.status_code == 200 and b"Not computed yet" in page.data
    assert client.post("/dispersion/etf/ETF/maturities/run", data={"date": day}).status_code == 302
    client.post("/dispersion/etf/ETF/maturities/run", data={"date": day})              # still starting: no 2nd job
    assert launched == [("ETF", day)]
    assert b"refreshes every 10 s" in client.get(f"/dispersion/etf/ETF/maturities?date={day}").data
    assert client.post("/dispersion/etf/NOPE/maturities/run", data={"date": day}).status_code == 404
    assert client.post("/dispersion/etf/ETF/maturities/run", data={"date": "../x"}).status_code == 404
    from src.application.managers.project_managers.etf_dispersion_screener_project import maturities
    maturities.run("ETF", day, market_data=FakeMarket(SPOTS, QUOTES), config={"results_dir": results},
                   now=lambda: datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc))
    done = client.get(f"/dispersion/etf/ETF/maturities?date={day}")
    assert done.status_code == 200 and str(EXPIRY).encode() in done.data and b"Run again" in done.data
    assert b"Hidden" not in done.data
