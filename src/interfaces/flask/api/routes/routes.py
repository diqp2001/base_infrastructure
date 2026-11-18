from src.interfaces.flask.api.controllers.backtest_controller import backtest_api
from src.interfaces.flask.api.controllers.research_controller import research_api


def register_api_routes(app):
    # Register all API blueprints here
    app.register_blueprint(backtest_api)
    app.register_blueprint(research_api)   # /api/backtests, /api/models  research / backtest registry (read only)
