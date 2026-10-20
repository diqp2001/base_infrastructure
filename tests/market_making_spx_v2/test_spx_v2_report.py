"""
SPX v2 performance report: built from results.json + data_report.txt (report.pkl / report.pdf) and served
read-only by the Flask dashboard (/spx_v2). No DB, no TWS.
"""

import json

import pytest

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting import (
    spx_report_store as store,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting.spx_report import (
    build_report, data_issues_from_text,
)

VALUES = [1_000_000.0, 999_000.0, 999_000.0, 1_002_000.0, 1_001_000.0]
DATA_REPORT = """DATA REPORT — market_making_spx_call_spread_v2
period 2026-08-05 16:00:00 .. 2026-08-11 16:00:00   bars 5

1. CHECKS AT START  (1 ok, 1 failed)
  [ok] universe entities created (5/5)
  [MISSING] SR3 contract of every backtest date in the universe (needed ['SR3U6'], registered ['SR3Z6'])
        missing — fetched from IBKR at run time or the risk-free rate fails: SR3U6 needed 2026-08-05 .. 2026-08-11

2. GREEKS THAT DID NOT RESOLVE  (4 distinct, 4 occurrences)
  - SPY   281215C00775000  delta: 1 bar(s), 2026-08-06 16:00:00 .. 2026-08-06 16:00:00
    root cause: CompanyShareOptionFactor 'close' no_observation: no usable observation at 2026-08-06 16:00:00: latest stored 2026-08-05
    dependency tree (first occurrence):
      CompanyShareOptionDeltaFactor 'delta'  MISSING
  - SPY   281215C00775000  gamma: 1 bar(s), 2026-08-06 16:00:00 .. 2026-08-06 16:00:00
    root cause: CompanyShareOptionFactor 'close' no_observation: no usable observation at 2026-08-06 16:00:00: latest stored 2026-08-05
  - SPY   281215C00775000  delta: 1 bar(s), 2026-08-07 16:00:00 .. 2026-08-07 16:00:00
    root cause: CompanyShareOptionFactor 'close' no_observation: no usable observation at 2026-08-07 16:00:00: latest stored 2026-08-05
  - SPY   281215C00775000  gamma: 1 bar(s), 2026-08-07 16:00:00 .. 2026-08-07 16:00:00
    root cause: CompanyShareOptionFactor 'close' no_observation: no usable observation at 2026-08-07 16:00:00: latest stored 2026-08-05

3. HEDGE DECIDED WITH POSITIONS MISSING GREEKS  (2 bar(s); those positions count as delta / gamma 0)
  2026-08-06 16:00:00  SPY   281215C00775000  book delta used: 0
"""


def summary():
    times = ["2026-08-05 16:00:00", "2026-08-06 16:00:00", "2026-08-07 16:00:00", "2026-08-10 16:00:00",
             "2026-08-11 16:00:00"]
    steps = [{"time": t, "option_order": None, "hedge_order": None, "positions": 1, "portfolio_delta": -100.0,
              "portfolio_gamma": -2.0, "hedge_spot": None, "note": "", "error": None} for t in times]
    steps[0].update(option_order={"CompanyShareOption": {"name": "SPY   281215C00775000", "weight": -0.2}},
                    hedge_order={"CompanyShare": {"name": "SPY", "quantity": 100.0}}, hedge_spot=770.0)
    steps[3].update(hedge_order={"CompanyShare": {"name": "SPY", "quantity": 98.0}}, hedge_spot=772.0)
    return {"project": "market_making_spx_call_spread_v2", "period": [times[0], times[-1]], "bars": 5,
            "option_entries": 1, "hedges": 2, "step_errors": [], "final_portfolio_value": VALUES[-1],
            "portfolio_values": [{"time": t, "value": v} for t, v in zip(times, VALUES)], "steps": steps,
            "execution_time_s": 12.0, "saved_at": "2026-10-20T12:00:00"}


@pytest.fixture
def results_dir(tmp_path):
    (tmp_path / store.RESULTS_FILE).write_text(json.dumps(summary()), encoding="utf-8")
    (tmp_path / store.DATA_REPORT_FILE).write_text(DATA_REPORT, encoding="utf-8")
    return tmp_path


def test_metrics_follow_the_portfolio_values():
    rep = build_report(summary(), DATA_REPORT)
    m = rep.metrics.iloc[0]
    assert m["Total Return"] == pytest.approx(VALUES[-1] / VALUES[0] - 1)
    assert m["MDD"] == pytest.approx(0.001)                               # 1 000 000 -> 999 000
    assert m["Hit Rate"] == pytest.approx(1 / 4)                          # one up bar of four returns
    assert rep.periods_per_year == pytest.approx(252)                     # one bar per day
    assert rep.drawdown.min() == pytest.approx(-0.001)


def test_orders_and_greeks_come_from_the_steps():
    rep = build_report(summary(), DATA_REPORT)
    assert list(rep.trades["kind"]) == ["option entry", "delta hedge", "delta hedge"]
    assert list(rep.trades["size"]) == [-0.2, 100.0, 98.0]
    assert rep.greeks["hedge"].sum() == 2 and rep.greeks["entry"].sum() == 1


def test_notes_flag_stale_values_and_missing_greeks():
    notes = " ".join(build_report(summary(), DATA_REPORT).notes)
    assert "unchanged on 1 of 4 bars" in notes
    assert "Greeks did not resolve on 2 bar(s)" in notes


def test_data_issues_are_grouped_by_root_cause_without_trees():
    issues = data_issues_from_text(DATA_REPORT)
    assert any("[MISSING] SR3 contract" in line for line in issues)
    grouped = [line for line in issues if line.startswith("  - ")]
    assert grouped == ["  - SPY   281215C00775000: delta, gamma missing on 2 bar(s) "
                       "(2026-08-06 16:00:00 .. 2026-08-07 16:00:00)"]
    assert not any("dependency tree" in line for line in issues)


def test_no_portfolio_value_no_report():
    assert build_report(dict(summary(), portfolio_values=[])) is None


def test_store_writes_pickle_and_pdf(results_dir):
    rep = store.build_from_files(str(results_dir))
    store.save_report(rep, str(results_dir))
    assert store.load_report(str(results_dir)).final_value == VALUES[-1]
    assert open(store.pdf_path(str(results_dir)), "rb").read(5) == b"%PDF-"


def test_flask_dashboard_results_and_pdf(results_dir):
    from flask import Flask

    from src.interfaces.flask.web.controllers.spx_v2_controller import spx_v2_bp
    import src.interfaces.flask.app as flask_app_module
    import os

    store.save_report(store.build_from_files(str(results_dir)), str(results_dir))
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(flask_app_module.__file__), "web", "templates"))
    app.config["SPX_V2_RESULTS_DIR"] = str(results_dir)
    app.register_blueprint(spx_v2_bp)
    client = app.test_client()

    assert client.get("/spx_v2/").status_code == 200
    snap = client.get("/spx_v2/api/progress").get_json()
    assert snap["has_report"] is True and snap["status"] == "idle"       # no progress.json in this folder
    page = client.get("/spx_v2/results")
    assert page.status_code == 200 and b"Table 1: Performance Metrics" in page.data
    pdf = client.get("/spx_v2/report.pdf")
    assert pdf.status_code == 200 and pdf.data[:5] == b"%PDF-"


def test_flask_results_without_a_report_is_404(tmp_path):
    from flask import Flask

    from src.interfaces.flask.web.controllers.spx_v2_controller import spx_v2_bp
    import src.interfaces.flask.app as flask_app_module
    import os

    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(flask_app_module.__file__), "web", "templates"))
    app.config["SPX_V2_RESULTS_DIR"] = str(tmp_path)
    app.register_blueprint(spx_v2_bp)
    client = app.test_client()
    assert client.get("/spx_v2/results").status_code == 404
    assert client.get("/spx_v2/report.pdf").status_code == 404
