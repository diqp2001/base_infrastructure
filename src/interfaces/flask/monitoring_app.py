"""
Stand-alone read-only monitoring website (the process to expose to a phone / private network).

Unlike ``app.py`` (development UI with upload / backtest routes), this Flask application only
registers the monitoring blueprint, and rejects every non-GET/HEAD/OPTIONS request globally.

Run (monitor compose service):
    gunicorn --workers 1 --threads 8 --bind 0.0.0.0:8050 src.interfaces.flask.monitoring_app:app
One worker on purpose: one background collector and one IBKR API connection per dashboard.
"""

import os

from flask import Flask, jsonify, redirect, request

from src.interfaces.flask.web.controllers.monitor_controller import SAFE_METHODS, create_monitor_blueprint


def create_monitoring_app(service_provider=None) -> Flask:
    if service_provider is None:
        from src.application.services.monitoring.service import get_monitoring_service
        service_provider = get_monitoring_service
    here = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, template_folder=os.path.join(here, "web", "templates"),
                static_folder=None)          # no generic static route: only the blueprint's assets
    app.config.update(JSON_SORT_KEYS=False, MAX_CONTENT_LENGTH=1024, PROPAGATE_EXCEPTIONS=False)

    @app.before_request
    def _read_only_everywhere():
        if request.method not in SAFE_METHODS:
            return jsonify({"error": "read-only dashboard: method not allowed"}), 405, {"Allow": "GET, HEAD, OPTIONS"}
        return None

    app.register_blueprint(create_monitor_blueprint(service_provider))

    @app.get("/")
    def root():
        return redirect("/monitor/", code=302)

    return app


app = create_monitoring_app()
