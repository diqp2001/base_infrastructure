# src/application/managers/web_managers/flask/views.py

import os
from flask import  render_template

def setup_routes(app):
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
    
    @app.app.route('/project/execute', methods=['POST'])
    def execute_project():
        """
        Endpoint to execute the project workflow.
        """
        self.project_manager.execute()
        return jsonify({"message": "Project executed successfully"}), 200

    @app.app.route('/project/results', methods=['GET'])
    def get_project_results():
        """
        Endpoint to retrieve the project's latest results.
        """
        results = self.project_manager.get_results()
        return jsonify(results), 200

    @app.app.route('/project/update_monthly', methods=['POST'])
    def update_monthly_data():
        """
        Endpoint to update monthly data for the project.
        """
        success = self.project_manager.update_monthly_data()
        return jsonify({"message": "Monthly data updated successfully" if success else "Update failed"}), 200 if success else 500

