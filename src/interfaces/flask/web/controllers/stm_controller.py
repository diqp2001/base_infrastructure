"""
Spatio-Temporal Momentum dashboard (read-only viewer).

Runs are started outside the web app (main.py, VS Code, ...).  Every run of
SpatioTemporalMomentumProjectManager writes its live progress and its final
report to the project's ``results_dir``; this blueprint only reads them, so a
run can be followed from a browser opened at any moment.

  GET /stm/               dashboard: live progress of the current / last run
  GET /stm/api/progress   progress snapshot (JSON, from progress.json)
  GET /stm/results        results window of the latest stored report
  GET /stm/report.pdf     PDF of the latest stored report

Every route takes ?project=<key> (see PROJECTS); default: the daily project.
"""

import io
import os
from datetime import datetime

import importlib
import importlib.util

from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_renderer as renderer
from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store as store
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import STMProgressTracker

stm_bp = Blueprint("stm", __name__, url_prefix="/stm")

# project key -> (label, config module of the project)
PROJECTS = {
    "daily": ("Daily clock", "src.application.managers.project_managers.spatio_temporal_momentum_project.config"),
    "5m": ("5-minute clock", "src.application.managers.project_managers.spatio_temporal_momentum_project_5m.config"),
    "full": ("Paper universe (46 US financials)",
             "src.application.managers.project_managers.spatio_temporal_momentum_project_full.config"),
    "10m": ("Paper universe, model trained on 10-minute bars",
            "src.application.managers.project_managers.spatio_temporal_momentum_project_10m.config"),
}


def _exists(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:          # parent package (project folder) missing
        return False


# keep only the projects whose folder exists (a project folder may be removed)
PROJECTS = {k: v for k, v in PROJECTS.items() if _exists(v[1])} or PROJECTS
_caches = {}


def _project() -> str:
    key = request.args.get("project", "daily")
    return key if key in PROJECTS else next(iter(PROJECTS))


def _results_dir() -> str:
    override = current_app.config.get("STM_RESULTS_DIR")
    if override:
        return override
    return importlib.import_module(PROJECTS[_project()][1]).get_config()["results_dir"]


def _cache() -> dict:
    return _caches.setdefault(_results_dir(), {"mtime": None, "report": None, "figures": {}, "pdf": None})


def _report():
    """Latest stored report of the selected project, reloaded only when the file changes."""
    results_dir = _results_dir()
    cache = _cache()
    mtime = store.report_mtime(results_dir)
    if mtime is None:
        return None
    if cache["mtime"] != mtime:
        cache.update(mtime=mtime, report=store.load_report(results_dir), figures={}, pdf=None)
    return cache["report"]


@stm_bp.route("/")
def dashboard():
    return render_template("stm_dashboard.html", projects={k: v[0] for k, v in PROJECTS.items()},
                           project=_project())


@stm_bp.route("/api/progress")
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


@stm_bp.route("/results")
def results():
    report = _report()
    if report is None:
        return render_template("stm_results.html", report=None, project_label=PROJECTS[_project()][0]), 404
    figures = _cache()["figures"]
    for key in renderer.FIGURES:
        if key not in figures:
            figures[key] = renderer.figure_base64(report, key)
    tables = {key: (title, renderer.table_html(df)) for key, title, df in renderer.tables(report)}
    sections = []
    for key in renderer.PAPER_ORDER:
        if key in tables:
            sections.append({"kind": "table", "title": tables[key][0], "html": tables[key][1]})
        else:
            sections.append({"kind": "figure", "title": renderer.FIGURES[key][0], "png": figures[key]})
    return render_template("stm_results.html", report=report, sections=sections,
                           project=_project(), project_label=PROJECTS[_project()][0])


@stm_bp.route("/report.pdf")
def report_pdf():
    report = _report()
    if report is None:
        return jsonify({"error": "no stored report yet"}), 404
    cache = _cache()
    stored = store.pdf_path(_results_dir())
    if stored and os.path.getmtime(stored) >= cache["mtime"]:
        data = open(stored, "rb").read()
    else:
        if cache["pdf"] is None:
            cache["pdf"] = renderer.build_pdf(report)
        data = cache["pdf"]
    suffix = "" if _project() == "daily" else f"_{_project()}"
    return send_file(io.BytesIO(data), mimetype="application/pdf", as_attachment=True,
                     download_name=f"spatio_temporal_momentum{suffix}_report.pdf")
