"""
Stand-alone read-only research / backtest registry app: the /research pages and the /api/backtests, /api/models API.

    python -m src.interfaces.flask.research_app          # 127.0.0.1:8053 (waitress if installed, else Flask)
Every non-GET/HEAD/OPTIONS request is refused, and the database session carries the monitor's write guard.
"""

import os

from flask import Flask, jsonify, redirect, request

from src.interfaces.flask.api.controllers.research_controller import research_api
from src.interfaces.flask.web.controllers.research_registry_controller import research_registry_bp

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def create_app(services_factory=None) -> Flask:
    here = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, template_folder=os.path.join(here, "web", "templates"),
                static_folder=os.path.join(here, "web", "static"))      # the shared theme (css/theme.css)
    if services_factory is not None:
        app.config["RESEARCH_SERVICES_FACTORY"] = services_factory

    @app.before_request
    def _read_only():
        if request.method not in SAFE_METHODS:
            return jsonify({"error": "read-only application"}), 405
        return None

    app.register_blueprint(research_api)
    app.register_blueprint(research_registry_bp)

    @app.get("/")
    def root():
        return redirect("/research/", code=302)

    return app


if __name__ == "__main__":
    port = int(os.getenv("RESEARCH_APP_PORT", "8053"))
    application = create_app()
    try:
        from waitress import serve
        serve(application, host="127.0.0.1", port=port, threads=4)
    except ImportError:
        application.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
