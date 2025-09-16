from src.interfaces.flask.api.controllers.backtest_controller import backtest_api

def register_api_routes(app):
    # Register all API blueprints here
    app.register_blueprint(backtest_api)
