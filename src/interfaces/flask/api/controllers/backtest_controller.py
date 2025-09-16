from flask import Blueprint, request, jsonify
from application.services.misbuffet import Misbuffet

backtest_api = Blueprint("backtest_api", __name__)

@backtest_api.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.json  # JSON body
    service = Misbuffet()
    results = service.run(params)
    return jsonify(results.to_dict())
