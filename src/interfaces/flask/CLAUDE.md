src/
  application/
    services/                👈 use cases (already here)
  domain/
    entities/
    ports/
  infrastructure/
    repositories/
    models/
  interfaces/
    flask/
        web/                     👈 HTML views + controllers
            controllers/
            templates/
            static/
        api/                     👈 REST/JSON API
            controllers/
            routes/
                routes.py
        flask.py
  main.py


  Separation of Concerns

Web → controllers render Jinja2 templates, return HTML pages.

API → controllers return JSON (Flask jsonify), no HTML.

Both layers call the same application services (e.g. BacktestService, PortfolioService)


 📂 interfaces/flask/flask.py

FlaskApp is only in the interfaces layer → no domain logic.

Web & API logic live under interfaces/flask/web and interfaces/flask/api.

application.services are called inside controllers, not here.

This class is just glue: app creation, config, and route registration.

📂 interfaces/flask/

This is your presentation layer (interface adapters in DDD).
It connects the outside world (HTTP requests) to your application services.
Everything Flask-specific stays here, isolated from your domain logic.

📂 web/

This is your HTML-based UI (dashboards, forms, reports).

controllers/ → Flask view controllers that handle HTTP requests, call application.services, and render templates.

templates/ → Jinja2 HTML templates. Can be designed in a tool like Bootstrap Studio / Figma → HTML → drop here.

static/ → Static assets like CSS, JS, images. Served directly by Flask.

👉 Typical flow: request → web.controller → application.service → template (HTML)

📂 api/

This is your REST/JSON interface (programmatic access).

controllers/ → Functions (Flask blueprints) that handle API endpoints, call application.services, and return JSON responses.

routes/ → Organize your API route definitions (e.g. routes.py for registering endpoints). Keeps controllers thin and routes centralized.

👉 Typical flow: request → api.controller → application.service → JSON response

🔹 Roles in Summary

web/controllers/

Contains controllers for serving HTML.

Example: dashboard_controller.py (renders dashboard.html).

web/templates/

Contains .html files with Jinja2 placeholders for data from controllers.

web/static/

Assets: CSS, JS, images.

api/controllers/

API logic: each file groups endpoints by domain (e.g. backtest_controller.py).

Thin: should just validate request, call service, format response.

api/routes/

Route registrations.

Keeps blueprints and URL structures organized. Example: routes.py might register /api/backtest with the backtest_controller.

✅ This way:

Your web UI and API are cleanly separated.

Both call into application/services (so business logic is reused).

Flask never leaks into domain or infrastructure.


examples:


interfaces/api/routes/routes.py:

from flask import Blueprint, request, jsonify
from application.services.backtest_service import BacktestService

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.json
    service = BacktestService()
    results = service.run(params)
    return jsonify(results.to_dict())

interfaces/web/controllers/dashboard_controller.py:
from flask import Blueprint, render_template, request
from application.services.backtest_service import BacktestService

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def home():
    return render_template("index.html")

@web_bp.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.form
    service = BacktestService()
    results = service.run(params)
    return render_template("results.html", results=results)
