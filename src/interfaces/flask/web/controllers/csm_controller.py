"""
/csm — read-only dashboard of the cross-sectional momentum project (LightGBM + Optuna TPE).

Runs are started outside the web app (e.g. src/main.py); the project writes its live progress and final results
to its results_dir, which this blueprint only reads:

    GET /csm/               progress page (polls /csm/api/progress)
    GET /csm/api/progress   live progress JSON
    GET /csm/results        latest stored results (performance, feature importance, Optuna, data coverage)
    GET /csm/report.pdf     the same report as a PDF
"""

import importlib
import io
import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from src.application.services.data.entities.factor.cross_sectional_momentum import csm_report_renderer as renderer
from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store as store
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import STMProgressTracker

csm_bp = Blueprint("csm", __name__, url_prefix="/csm")

PROJECTS = {
    "cross_sectional": ("Paper universe, LightGBM + Optuna TPE",
                        "src.application.managers.project_managers.cross_sectionnal_project.config"),
}
_caches = {}


def _project() -> str:
    key = request.args.get("project", "cross_sectional")
    return key if key in PROJECTS else next(iter(PROJECTS))


def _results_dir() -> str:
    override = current_app.config.get("CSM_RESULTS_DIR")
    if override:
        return override
    return importlib.import_module(PROJECTS[_project()][1]).get_config()["results_dir"]


def _cache() -> dict:
    return _caches.setdefault(_results_dir(), {"mtime": None, "report": None, "figures": {}, "pdf": None})


def _report():
    results_dir = _results_dir()
    cache = _cache()
    mtime = store.report_mtime(results_dir)
    if mtime is None:
        return None
    if cache["mtime"] != mtime:
        cache.update(mtime=mtime, report=store.load_report(results_dir), figures={}, pdf=None)
    return cache["report"]


@csm_bp.route("/")
def dashboard():
    return render_template("csm_dashboard.html", projects={k: v[0] for k, v in PROJECTS.items()},
                           project=_project())


@csm_bp.route("/api/progress")
def progress():
    results_dir = _results_dir()
    snap = STMProgressTracker.read_snapshot(store.progress_path(results_dir)) or {
        "status": "idle", "phase": "", "bars_done": 0, "bars_total": None, "percent": None,
        "retrainings": [], "trained_sessions": 0, "log": [], "last_epoch": None,
        "portfolio_value": None, "current_session": None, "error": None,
    }
    mtime = store.report_mtime(results_dir)
    snap["has_report"] = mtime is not None
    snap["report_saved_at"] = datetime.fromtimestamp(mtime).isoformat(timespec="seconds") if mtime else None
    if snap.get("updated_at"):
        age = (datetime.now() - datetime.fromisoformat(snap["updated_at"])).total_seconds()
        snap["seconds_since_update"] = round(age)
    snap["results_dir"] = results_dir
    snap["project"] = _project()
    return jsonify(snap)


@csm_bp.route("/results")
def results():
    report = _report()
    label = PROJECTS[_project()][0]
    if report is None:
        return render_template("csm_results.html", report=None, project_label=label), 404
    figures = _cache()["figures"]
    for key in renderer.FIGURES:
        if key not in figures:
            figures[key] = renderer.figure_base64(report, key)
    tables = {key: (title, renderer.table_html(df)) for key, title, df in renderer.tables(report) if df is not None}
    sections = []
    for key in renderer.ORDER:
        if key in tables:
            sections.append({"kind": "table", "title": tables[key][0], "html": tables[key][1]})
        elif key in renderer.FIGURES:
            sections.append({"kind": "figure", "title": renderer.FIGURES[key][0], "png": figures[key]})
    return render_template("csm_results.html", report=report, sections=sections, project=_project(),
                           project_label=label)


@csm_bp.route("/report.pdf")
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
                     download_name="cross_sectional_momentum_report.pdf")
