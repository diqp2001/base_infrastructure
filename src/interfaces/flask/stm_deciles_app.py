"""
Stand-alone read-only page of the monthly STM decile backtest (/stm-deciles/).

    python -m src.interfaces.flask.stm_deciles_app            # 127.0.0.1:8052 (waitress if installed, else Flask)
    gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8052 src.interfaces.flask.stm_deciles_app:app
Every non-GET/HEAD/OPTIONS request is refused; it only reads results/stm_monthly_deciles/.
"""

import os

from flask import Flask, jsonify, redirect, request

from src.interfaces.flask.web.controllers.stm_deciles_controller import create_stm_deciles_blueprint

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def create_app(results_dir=None) -> Flask:
    app = Flask(__name__, static_folder=None)

    @app.before_request
    def _read_only():
        if request.method not in SAFE_METHODS:
            return jsonify({"error": "read-only page"}), 405
        return None

    app.register_blueprint(create_stm_deciles_blueprint(results_dir))

    @app.get("/")
    def root():
        return redirect("/stm-deciles/", code=302)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("STM_DECILES_PORT", "8052"))
    try:
        from waitress import serve
        serve(app, host="127.0.0.1", port=port, threads=4)
    except ImportError:
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
