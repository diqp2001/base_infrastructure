"""
Stand-alone read-only page of the monthly model-filtered dispersion backtest (/dispersion-stm/).

    gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8051 src.interfaces.flask.dispersion_stm_app:app
Every non-GET/HEAD/OPTIONS request is refused; it only reads results/etf_dispersion_stm/.
"""

from flask import Flask, jsonify, redirect, request

from src.interfaces.flask.web.controllers.dispersion_stm_controller import create_dispersion_stm_blueprint

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def create_app(results_dir=None) -> Flask:
    app = Flask(__name__, static_folder=None)

    @app.before_request
    def _read_only():
        if request.method not in SAFE_METHODS:
            return jsonify({"error": "read-only page"}), 405
        return None

    app.register_blueprint(create_dispersion_stm_blueprint(results_dir))

    @app.get("/")
    def root():
        return redirect("/dispersion-stm/", code=302)

    return app


app = create_app()
