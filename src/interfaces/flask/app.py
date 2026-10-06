import os
from flask import Flask
from src.interfaces.flask.web.controllers.dashboard_controller import web_bp
from src.interfaces.flask.web.controllers.entity_upload_controller import entity_upload_bp
from src.interfaces.flask.web.controllers.stm_controller import stm_bp
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

        # Register API routes
        register_api_routes(self.app)

    def run(self, **kwargs):
        """Start the Flask app"""
        self.app.run(**kwargs)

    def get_app(self):
        """Expose the underlying Flask app (for testing or WSGI servers)"""
        return self.app


app = FlaskApp().app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)