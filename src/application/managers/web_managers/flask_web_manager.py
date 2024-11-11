# src/application/managers/web_managers/flask_web_manager.py

from flask import Flask, render_template
from src.application.managers.web_managers.web_manager import WebManager
from src.application.managers.web_managers.views import setup_routes  # Import the route setup function

class FlaskWebManager(WebManager):
    """
    FlaskWebManager class, a child of WebManager, for managing a Flask web application.
    Configures template and static file paths, loads routes from `views.py`.
    """

    def __init__(self, host='127.0.0.1', port=5000, app_name='FlaskApp'):
        """
        Initialize the FlaskWebManager with a Flask app, setting up templates and static folders.
        """
        super().__init__(host, port)
        self.app = Flask(app_name, template_folder="templates", static_folder="static")
        self.app_name = app_name
        setup_routes(self.app)  # Load routes from views.py
        print(f"Initialized FlaskWebManager with app '{self.app_name}'")

    def start_server(self):
        """
        Start the Flask web server.
        """
        try:
            print(f"Starting Flask app '{self.app_name}' on {self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port)
        except Exception as e:
            print(f"Error starting Flask app '{self.app_name}': {e}")
