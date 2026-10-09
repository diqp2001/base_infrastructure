"""
Read-only monitoring dashboard (no login; access is restricted at the network level).

Pages:  /monitor/  /monitor/ibkr  /monitor/infrastructure  /monitor/market-data
        /monitor/factors  /monitor/logs  /monitor/settings
API:    GET /monitor/api/health | status | status/connections | status/database | status/ibkr
            account/summary | account/positions | account/orders | market-data/status
            factors/status | jobs/status | logs/recent | config

Read-only enforcement in this layer:
* only GET / HEAD / OPTIONS are accepted (anything else -> 405 before any handler runs);
* handlers only call MonitoringService read views (no repositories, no broker, no services that
  can write); query parameters are validated and bounded;
* every JSON response is passed through redaction; responses are never cached.
"""

from typing import Any, Callable, Dict, Optional

from flask import Blueprint, abort, jsonify, render_template, request

from src.application.services.monitoring.log_store import COMPONENTS, LEVELS
from src.application.services.monitoring.redaction import redact
from src.application.services.monitoring.status import iso, utcnow

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PAGES = (
    ("overview", "/", "Overview"),
    ("ibkr", "/ibkr", "IBKR & account"),
    ("infrastructure", "/infrastructure", "Infrastructure"),
    ("market_data", "/market-data", "Market data"),
    ("factors", "/factors", "Factors & jobs"),
    ("logs", "/logs", "Logs"),
    ("settings", "/settings", "Settings"),
)


def _int_arg(name: str, default: int, lo: int, hi: int) -> int:
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        abort(400, description=f"{name} must be an integer")
    if not lo <= value <= hi:
        abort(400, description=f"{name} must be between {lo} and {hi}")
    return value


def _choice_arg(name: str, choices, default: Optional[str]) -> Optional[str]:
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    if raw not in choices:
        abort(400, description=f"{name} must be one of {sorted(choices)}")
    return raw


def _text_arg(name: str, max_len: int = 100) -> Optional[str]:
    raw = request.args.get(name)
    if not raw:
        return None
    return raw.strip()[:max_len] or None


def create_monitor_blueprint(service_provider: Callable[[], Any]) -> Blueprint:
    bp = Blueprint("monitor", __name__, url_prefix="/monitor",
                   template_folder="../templates", static_folder="../static/monitor",
                   static_url_path="/static")

    def svc():
        service = service_provider()
        service.start()                      # idempotent; lazy so the Flask reloader parent stays idle
        return service

    @bp.before_request
    def _reject_mutations():
        if request.method not in SAFE_METHODS:
            return jsonify({"error": "read-only dashboard: method not allowed", "method": request.method}), 405, \
                {"Allow": "GET, HEAD, OPTIONS"}
        return None

    @bp.after_request
    def _headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
        return response

    def api(payload: Dict[str, Any], status_code: int = 200):
        payload = dict(payload)
        payload["generated_at"] = iso(utcnow())
        return jsonify(redact(payload)), status_code

    # ------------------------------------------------------------------ pages
    def page(name: str):
        def view():
            service = svc()
            iv = service.config.intervals
            return render_template(f"monitor/{name}.html", pages=PAGES, active=name, intervals=iv,
                                   environment=service.config.environment, version=service.config.version,
                                   components=COMPONENTS, levels=list(LEVELS))
        view.__name__ = f"page_{name}"
        return view

    for name, path, _title in PAGES:
        bp.add_url_rule(path, endpoint=f"page_{name}", view_func=page(name), methods=["GET"])

    # ------------------------------------------------------------------ API
    @bp.get("/api/health")
    def api_health():
        service = svc()
        app_view = service.application()
        return api({"status": app_view["status"] if app_view["status"] != "unknown" else "healthy",
                    "service": "monitoring-dashboard", "read_only": True,
                    "uptime_seconds": app_view["data"]["uptime_seconds"]})

    @bp.get("/api/status")
    def api_status():
        return api(svc().overview())

    @bp.get("/api/status/connections")
    def api_connections():
        return api(svc().connections())

    @bp.get("/api/status/database")
    def api_database():
        return api(svc().database())

    @bp.get("/api/status/ibkr")
    def api_ibkr():
        return api(svc().ibkr_connection())

    @bp.get("/api/account/summary")
    def api_account_summary():
        return api(svc().account_summary())

    @bp.get("/api/account/positions")
    def api_positions():
        return api(svc().positions())

    @bp.get("/api/account/orders")
    def api_orders():
        return api(svc().orders())

    @bp.get("/api/market-data/status")
    def api_market_data():
        limit = _int_arg("limit", 200, 1, 1000)
        stale_only = _choice_arg("stale_only", {"0", "1", "true", "false"}, "0") in ("1", "true")
        return api(svc().market_data(limit=limit, stale_only=stale_only, query=_text_arg("q")))

    @bp.get("/api/factors/status")
    def api_factors():
        return api(svc().factors(limit=_int_arg("limit", 200, 1, 1000), query=_text_arg("q")))

    @bp.get("/api/jobs/status")
    def api_jobs():
        return api(svc().jobs_status(limit=_int_arg("limit", 100, 1, 500)))

    @bp.get("/api/logs/recent")
    def api_logs():
        return api(svc().recent_logs(
            level=_choice_arg("level", set(LEVELS), "INFO"),
            component=_choice_arg("component", set(COMPONENTS), None),
            since_minutes=_int_arg("since_minutes", 0, 0, 10080) or None,
            query=_text_arg("q"),
            limit=_int_arg("limit", 200, 1, 1000)))

    @bp.get("/api/config")
    def api_config():
        return api(svc().safe_config())

    @bp.errorhandler(400)
    def _bad_request(e):
        return jsonify({"error": getattr(e, "description", "bad request")}), 400

    return bp
