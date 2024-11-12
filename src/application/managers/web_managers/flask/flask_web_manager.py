# src/application/managers/web_managers/flask/flask_web_manager.py 

from flask import Flask, render_template
from src.application.managers.web_managers.web_manager import WebManager
from src.application.managers.web_managers.flask.views import setup_routes

class FlaskWebManager(WebManager):
    def __init__(self, host='127.0.0.1', port=5000, app_name='FlaskApp'):
        super().__init__(host, port)
        self._flask_app = Flask(app_name, template_folder="./templates", static_folder="./static")
        self.app_name = app_name
        setup_routes(self._flask_app)
        print(f"Initialized FlaskWebManager with app '{self.app_name}'")

    def start_server(self):
        try:
            print(f"Starting Flask app '{self.app_name}' on {self.host}:{self.port}")
            self._flask_app.run(host=self.host, port=self.port)
        except Exception as e:
            print(f"Error starting Flask app '{self.app_name}': {e}")

app = FlaskWebManager()._flask_app

if __name__ == "__main__":
    FlaskWebManager().start_server()
