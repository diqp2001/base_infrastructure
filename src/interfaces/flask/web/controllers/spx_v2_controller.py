"""
SPX call spread market maker (v2) dashboard (read-only viewer), same layout as the STM dashboard.

Runs are started outside the web app (main.py, VS Code, ...). Every run of
MarketMakingSPXCallSpreadV2ProjectManager writes its live progress and, at the end, its report to the
project's ``results_dir``; this blueprint only reads them, so a run can be followed from a browser opened
at any moment.

  GET /spx_v2/               dashboard: live progress of the current / last run
  GET /spx_v2/api/progress   progress snapshot (JSON, from progress.json)
  GET /spx_v2/results        results window of the latest stored report
  GET /spx_v2/report.pdf     PDF of the latest stored report
"""

import io
import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, send_file

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting import (
    spx_report_renderer as renderer,
    spx_report_store as store,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.utils.progress import (
    MMProgressTracker,
)

spx_v2_bp = Blueprint("spx_v2", __name__, url_prefix="/spx_v2")
_caches = {}


def _results_dir() -> str:
    override = current_app.config.get("SPX_V2_RESULTS_DIR")
    if override:
        return override
    from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config
    return config.get_config()["results_dir"]


def _cache() -> dict:
    return _caches.setdefault(_results_dir(), {"mtime": None, "report": None, "figures": {}, "pdf": None})


def _report():
    """Latest stored report, reloaded only when the file changes."""
    results_dir = _results_dir()
    cache = _cache()
    mtime = store.report_mtime(results_dir)
    if mtime is None:
        return None
    if cache["mtime"] != mtime:
        cache.update(mtime=mtime, report=store.load_report(results_dir), figures={}, pdf=None)
    return cache["report"]


@spx_v2_bp.route("/")
def dashboard():
    return render_template("spx_v2_dashboard.html")


@spx_v2_bp.route("/api/progress")
def progress():
    results_dir = _results_dir()
    snap = MMProgressTracker.read_snapshot(store.progress_path(results_dir)) or {
        "status": "idle", "phase": "", "bars_done": 0, "bars_total": None, "percent": None,
        "option_entries": 0, "hedges": 0, "step_errors": 0, "portfolio_value": None, "last_step": None,
        "log": [], "error": None,
    }
    snap.pop("summary", None)                       # the full summary is large; the results page shows it
    mtime = store.report_mtime(results_dir)
    snap["has_report"] = mtime is not None
    snap["report_saved_at"] = datetime.fromtimestamp(mtime).isoformat(timespec="seconds") if mtime else None
    if snap.get("updated_at"):
        age = (datetime.now() - datetime.fromisoformat(snap["updated_at"])).total_seconds()
        snap["seconds_since_update"] = round(age)
    snap["results_dir"] = results_dir
    return jsonify(snap)


@spx_v2_bp.route("/results")
def results():
    report = _report()
    if report is None:
        return render_template("spx_v2_results.html", report=None), 404
    figures = _cache()["figures"]
    for key in renderer.FIGURES:
        if key not in figures:
            figures[key] = renderer.figure_base64(report, key)
    tables = {key: (title, renderer.table_html(df)) for key, title, df in renderer.tables(report)}
    sections = []
    for key in renderer.ORDER:
        if key in tables:
            sections.append({"kind": "table", "title": tables[key][0], "html": tables[key][1]})
        else:
            sections.append({"kind": "figure", "title": renderer.FIGURES[key][0], "png": figures[key]})
    return render_template("spx_v2_results.html", report=report, sections=sections)


@spx_v2_bp.route("/report.pdf")
def report_pdf():
    report = _report()
    if report is None:
        return jsonify({"error": "no stored report yet"}), 404
    cache = _cache()
    stored = store.pdf_path(_results_dir())
    if stored and os.path.getmtime(stored) >= cache["mtime"]:
        with open(stored, "rb") as f:
            data = f.read()
    else:
        if cache["pdf"] is None:
            cache["pdf"] = renderer.build_pdf(report)
        data = cache["pdf"]
    return send_file(io.BytesIO(data), mimetype="application/pdf", as_attachment=True,
                     download_name="market_making_spx_call_spread_v2_report.pdf")
