"""
/research - generic research / backtest registry pages (2026-11-18). Read only; every route goes through
ResearchQueryService (the same services as /api/backtests and /api/models).

    GET /research/                       runs: filters (project, model, status, universe, created), headline metrics
    GET /research/runs/<id>              overview, progress, engine performance, equity, research series, metrics
    GET /research/compare?run_ids=1,2    comparability warnings, differences, config diff, metrics, equity overlay
    GET /research/models                 models
    GET /research/models/<id>            version, algorithm, features, training configuration / metrics, artifacts,
                                         runs using it (with each run's universe)

Long backtests are never run here: launch them from /strategies (separate worker) or as their own process.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from flask import Blueprint, abort, render_template, request

from src.interfaces.flask.api.controllers.research_controller import (
    close_research_services,
    plain,
    research_services,
    run_filters,
)

research_registry_bp = Blueprint("research_registry", __name__, url_prefix="/research")
research_registry_bp.teardown_app_request(close_research_services)

# categorical palette, dark steps, fixed order (validated: docs dataviz palette) - never cycled past 8
SERIES_COLORS = ("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767")
SINGLE_COLOR = SERIES_COLORS[0]
STATUSES = ("PENDING", "RUNNING", "COMPLETED", "PARTIAL", "FAILED", "CANCELLED")
PERCENT_METRICS = {"cumulative_return", "total_return", "annualized_return", "annualized_volatility", "volatility",
                   "max_drawdown", "win_rate", "best_day", "worst_day"}


def chart_spec(series: List[Dict[str, Any]], fmt: str = "num", baseline=None, label: str = "") -> str:
    return json.dumps({"series": series, "format": fmt, "baseline": baseline, "label": label})


def _points(points) -> List[list]:
    return [[p["date"], p["value"]] for p in points]


def fmt_metric(name: str, value) -> str:
    if value is None:
        return "–"
    if any(name.endswith(k) for k in PERCENT_METRICS):
        return f"{value * 100:+.2f}%" if "return" in name else f"{value * 100:.2f}%"
    if name.endswith("total_trading_days") or name.endswith("periods"):
        return f"{value:,.0f}"
    return f"{value:,.3f}" if abs(value) < 1000 else f"{value:,.0f}"


def fraction(run: Dict[str, Any]) -> float:
    planned, done = run.get("months_planned"), run.get("months_completed") or 0
    return min(1.0, done / planned) if planned else 0.0


@research_registry_bp.app_template_filter("metric")
def _metric_filter(value, name=""):
    return fmt_metric(name, value)


@research_registry_bp.route("/")
def runs():
    services = research_services()
    filters = run_filters()
    rows = services.list_runs(**filters)
    return render_template("research_registry/runs.html", runs=plain(rows), filters=filters,
                           projects=services.projects(), models=services.list_models(), statuses=STATUSES,
                           fraction=fraction)


@research_registry_bp.route("/runs/<int:run_id>")
def run(run_id: int):
    services = research_services()
    detail = services.run(run_id)
    if detail is None:
        abort(404)
    equity = services.equity(run_id)
    curves = [p for p in equity["portfolios"] if p["points"]]
    equity_chart = chart_spec([{"name": p["name"] or f"portfolio {p['portfolio_id']}", "color": SERIES_COLORS[i % 8],
                                "points": _points(p["points"])} for i, p in enumerate(curves[:8])],
                              fmt="num", label="Portfolio value") if curves else None
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for s in services.series(run_id, max_points=600)["series"]:
        groups.setdefault(s["group"] or "series", []).append(
            {"name": s["name"], "chart": chart_spec([{"name": s["name"], "color": SINGLE_COLOR,
                                                      "points": _points(s["points"])}], fmt="num", baseline=0,
                                                    label=s["name"]),
             "last": next((p["value"] for p in reversed(s["points"]) if p["value"] is not None), None),
             "points": len(s["points"])})
    metrics = services.metrics(run_id)
    return render_template("research_registry/run.html", run=plain(detail), equity_chart=equity_chart,
                           groups=groups, metrics=metrics, fraction=fraction,
                           config_json=json.dumps(plain(detail.get("config_snapshot")), indent=1, sort_keys=True))


@research_registry_bp.route("/compare")
def compare():
    try:
        ids = [int(x) for x in (request.args.get("run_ids") or "").split(",") if x.strip()]
    except ValueError:
        abort(400)
    if len(ids) < 2:
        return render_template("research_registry/compare.html", result=None, ids=ids, chart=None)
    try:
        result = research_services().compare(ids)
    except LookupError as e:
        abort(404, str(e))
    overlay = result["equity"][:8]
    chart = chart_spec([{"name": c["label"] + ("" if c["status"] == "COMPLETED" else f" ({c['status']})"),
                         "color": SERIES_COLORS[i], "points": _points(c["points"])} for i, c in enumerate(overlay)],
                       fmt="ratio", baseline=1.0, label="Equity, rebased to 1")
    return render_template("research_registry/compare.html", result=plain(result), ids=ids, chart=chart,
                           overflow=len(result["equity"]) > 8, fraction=fraction)


@research_registry_bp.route("/models")
def models():
    return render_template("research_registry/models.html", models=plain(research_services().list_models()))


@research_registry_bp.route("/models/<int:model_id>")
def model(model_id: int):
    services = research_services()
    m = services.model(model_id)
    if m is None:
        abort(404)
    return render_template("research_registry/model.html", model=plain(m),
                           artifacts=plain(services.model_artifacts(model_id)),
                           config_json=json.dumps(plain(m.get("configuration")), indent=1, sort_keys=True))
