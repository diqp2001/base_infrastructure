from flask import Blueprint, render_template, request
from src.application.services.misbuffet import Misbuffet

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def home():
    return render_template("index.html")

@web_bp.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.form  # values from an HTML form
    service = Misbuffet()
    results = service.run(params)  # returns a domain object or dict
    return render_template("results.html", results=results)
