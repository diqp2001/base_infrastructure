import os
from flask import Flask
from src.interfaces.flask.web.controllers.dashboard_controller import web_bp
from src.interfaces.flask.web.controllers.entity_upload_controller import entity_upload_bp
from src.interfaces.flask.web.controllers.stm_controller import stm_bp
from src.interfaces.flask.web.controllers.csm_controller import csm_bp
from src.interfaces.flask.web.controllers.spx_v2_controller import spx_v2_bp
from src.interfaces.flask.web.controllers.strategy_controller import strategies_bp
from src.interfaces.flask.web.controllers.factor_analysis_controller import factor_analysis_bp
from src.interfaces.flask.web.controllers.factor_research_controller import factor_research_bp
from src.interfaces.flask.api.routes.routes import register_api_routes


class FlaskApp:
    def __init__(self):
        # Define paths for templates and static files
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, 'web', 'templates')
        static_dir = os.path.join(current_dir, 'web', 'static')

        # Create the Flask app with proper template and static directories
        self.app = Flask(__name__,
                        template_folder=template_dir,
                        static_folder=static_dir)
        self.app.secret_key = "secret-key"

        # Register blueprints
        self._register_routes()

    def _register_routes(self):
        # Register web routes
        self.app.register_blueprint(web_bp)
        self.app.register_blueprint(entity_upload_bp)
        self.app.register_blueprint(stm_bp)          # /stm  Spatio-Temporal Momentum dashboard
        self.app.register_blueprint(csm_bp)          # /csm  Cross-sectional momentum (LightGBM + Optuna) dashboard
        self.app.register_blueprint(spx_v2_bp)       # /spx_v2  SPX call spread market maker (v2) dashboard
        self.app.register_blueprint(strategies_bp)   # /strategies  configure, launch and compare experiments
        self.app.register_blueprint(factor_analysis_bp)   # /factor-analysis  CAPM / Fama-French analysis of results
        self.app.register_blueprint(factor_research_bp)   # /powerbuffet/generate, /powerbuffet/research

        # Register API routes
        register_api_routes(self.app)

        # Read-only monitoring dashboard (/monitor). For phone / remote access use the dedicated
        # monitoring-only app (src/interfaces/flask/monitoring_app.py, compose service "monitor"),
        # never this development app, which also exposes upload / backtest routes.
        from src.application.services.monitoring.service import get_monitoring_service
        from src.interfaces.flask.web.controllers.monitor_controller import create_monitor_blueprint
        self.app.register_blueprint(create_monitor_blueprint(get_monitoring_service))

    def run(self, **kwargs):
        """Start the Flask app"""
        self.app.run(**kwargs)

    def get_app(self):
        """Expose the underlying Flask app (for testing or WSGI servers)"""
        return self.app


app = FlaskApp().app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)