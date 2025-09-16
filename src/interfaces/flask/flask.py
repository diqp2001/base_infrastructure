from flask import Flask
from src.interfaces.flask.web.controllers.dashboard_controller import web_bp
from src.interfaces.flask.api.routes.routes import register_api_routes


class FlaskApp:
    def __init__(self):
        # Create the Flask app
        self.app = Flask(__name__)
        
        # Register blueprints
        self._register_routes()

    def _register_routes(self):
        # Register web routes
        self.app.register_blueprint(web_bp)

        # Register API routes
        register_api_routes(self.app)

    def run(self, **kwargs):
        """Start the Flask app"""
        self.app.run(**kwargs)

    def get_app(self):
        """Expose the underlying Flask app (for testing or WSGI servers)"""
        return self.app