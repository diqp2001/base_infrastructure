"""
Research / backtest registry JSON API (2026-11-18). Read only: Flask -> ResearchQueryService -> repositories.

    GET /api/backtests                       ?project= &model_id= &status= &universe= &created_from= &created_to= &limit=
    GET /api/backtests/<run_id>
    GET /api/backtests/<run_id>/equity       ?max_points=
    GET /api/backtests/<run_id>/metrics
    GET /api/backtests/<run_id>/series       ?names=a,b &group= &max_points=
    GET /api/backtests/compare               ?run_ids=1,2,3
    GET /api/models
    GET /api/models/<model_id>
    GET /api/models/<model_id>/runs
    GET /api/models/<model_id>/artifacts

The services factory is ``app.config['RESEARCH_SERVICES_FACTORY']`` (tests inject one), else a read-only session on
the configured database.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, abort, current_app, g, jsonify, request

research_api = Blueprint("research_api", __name__, url_prefix="/api")


def research_services():
    """One ResearchQueryService (one read-only session) per request."""
    if "research_services" not in g:
        factory = current_app.config.get("RESEARCH_SERVICES_FACTORY")
        if factory is None:
            from src.application.services.backtest_registry.read_access import query_service_factory
            factory = query_service_factory()
            current_app.config["RESEARCH_SERVICES_FACTORY"] = factory
        g.research_services = factory()
    return g.research_services


def close_research_services(_exc=None):
    service = g.pop("research_services", None)
    if service is not None:
        from src.application.services.backtest_registry.read_access import close
        close(service)


research_api.teardown_app_request(close_research_services)


def plain(value):
    """JSON-safe: dates as ISO text, Decimal / NaN handled, nested containers walked."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [plain(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float) and value != value:
        return None
    return value


def _int_list(text):
    try:
        return [int(x) for x in (text or "").split(",") if x.strip()]
    except ValueError:
        abort(400, "run_ids must be integers separated by commas")


def _date_arg(name):
    text = request.args.get(name)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        abort(400, f"{name} must be an ISO date")


def run_filters():
    model_id = request.args.get("model_id", type=int)
    return {"project": request.args.get("project") or None, "model_id": model_id,
            "status": request.args.get("status") or None, "universe": request.args.get("universe") or None,
            "created_from": _date_arg("created_from"), "created_to": _date_arg("created_to"),
            "limit": min(request.args.get("limit", 200, type=int), 2000)}


@research_api.get("/backtests")
def list_backtests():
    return jsonify(plain(research_services().list_runs(**run_filters())))


@research_api.get("/backtests/compare")
def compare_backtests():
    ids = _int_list(request.args.get("run_ids"))
    if len(ids) < 2:
        abort(400, "compare needs at least two run_ids")
    try:
        return jsonify(plain(research_services().compare(ids)))
    except LookupError as e:
        abort(404, str(e))


@research_api.get("/backtests/<int:run_id>")
def get_backtest(run_id: int):
    run = research_services().run(run_id)
    if run is None:
        abort(404, f"run {run_id} not found")
    return jsonify(plain(run))


@research_api.get("/backtests/<int:run_id>/equity")
def backtest_equity(run_id: int):
    return jsonify(plain(research_services().equity(run_id, request.args.get("max_points", 1500, type=int))))


@research_api.get("/backtests/<int:run_id>/metrics")
def backtest_metrics(run_id: int):
    return jsonify(plain(research_services().metrics(run_id)))


@research_api.get("/backtests/<int:run_id>/series")
def backtest_series(run_id: int):
    names = [n for n in (request.args.get("names") or "").split(",") if n] or None
    return jsonify(plain(research_services().series(run_id, names=names, group=request.args.get("group") or None,
                                                   max_points=request.args.get("max_points", 1500, type=int))))


@research_api.get("/models")
def list_models():
    return jsonify(plain(research_services().list_models()))


@research_api.get("/models/<int:model_id>")
def get_model(model_id: int):
    model = research_services().model(model_id)
    if model is None:
        abort(404, f"model {model_id} not found")
    return jsonify(plain(model))


@research_api.get("/models/<int:model_id>/runs")
def model_runs(model_id: int):
    return jsonify(plain(research_services().model_runs(model_id)))


@research_api.get("/models/<int:model_id>/artifacts")
def model_artifacts(model_id: int):
    return jsonify(plain(research_services().model_artifacts(model_id)))
