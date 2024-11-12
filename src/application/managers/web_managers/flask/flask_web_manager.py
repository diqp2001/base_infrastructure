# src/application/managers/web_managers/flask/flask_web_manager.py 

import os
from flask import Flask, jsonify, render_template
from src.application.managers.web_managers.web_manager import WebManager
from src.application.managers.web_managers.flask.views import setup_routes

class FlaskWebManager(WebManager):
    def __init__(self, host='127.0.0.1', port=5000, app_name='FlaskApp'):
        super().__init__(host, port)
        self._flask_app = Flask(app_name, template_folder="./templates", static_folder="./static")
        self.app_name = app_name
        self.setup_routes(self._flask_app)
        print(f"Initialized FlaskWebManager with app '{self.app_name}'")

    def start_server(self):
        try:
            print(f"Starting Flask app '{self.app_name}' on {self.host}:{self.port}")
            self._flask_app.run(host=self.host, port=self.port)
        except Exception as e:
            print(f"Error starting Flask app '{self.app_name}': {e}")
    def setup_routes(self,app):
        """
        Sets up routes for the Flask app.
        :param app: Flask app instance to register routes with.
        """

        @app.route('/')
        def home():
            # Renders a template called 'base.html' (inside the templates folder)
            current_directory = os.getcwd()
            return "Hello, World!"
            #return render_template("./src/application/managers/web_managers/flask/templates/base.html")

        @app.route('/hello')
        def hello_world():
            return "Hello, World!"
        
        @app.route('/project/execute', methods=['POST'])
        def execute_project():
            """
            Endpoint to execute the project workflow.
            """
            #self.project_manager.execute()
            return jsonify({"message": "Project executed successfully"}), 200

        @app.route('/project/results', methods=['GET'])
        def get_project_results():
            """
            Endpoint to retrieve the project's latest results.
            """
            '''results = self.project_manager.get_results()
            return jsonify(results), 200'''
            return 'get_project_results'
        @app.route('/project/update_monthly', methods=['POST'])
        def update_monthly_data():
            """
            Endpoint to update monthly data for the project.
            """
            """
            success = self.project_manager.update_monthly_data()
            return jsonify({"message": "Monthly data updated successfully" if success else "Update failed"}), 200 if success else 500
            """
            return """update_monthly_data"""

app = FlaskWebManager()._flask_app

if __name__ == "__main__":
    FlaskWebManager().start_server()
