# src/application/managers/web_managers/views.py

from flask import render_template

def setup_routes(app):
    """
    Sets up routes for the Flask app.
    :param app: Flask app instance to register routes with.
    """

    @app.route('/')
    def home():
        # Renders a template called 'base.html' (inside the templates folder)
        return render_template("base.html")

    @app.route('/hello')
    def hello_world():
        return "Hello, World!"

    # Additional routes can be added here
