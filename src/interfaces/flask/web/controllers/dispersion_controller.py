"""
/dispersion — ETF dispersion-option screener results (P.08). Read-only views of the files a screening run writes
(results/etf_dispersion_screener/<date>/candidates.json, universe.json); runs are started outside the web app.

    /dispersion/                     latest run (or ?date=YYYY-MM-DD): ranked results table
    /dispersion/etf/<ticker>         detail of one candidate (ETF, constituents, trade, deltas, premiums)
    /dispersion/api/candidates       JSON (same ?date=)
    /dispersion/api/candidates/<etf> JSON of one candidate
"""

import json
import os
import re
from typing import List, Optional

from flask import Blueprint, abort, jsonify, render_template, request

from src.application.managers.project_managers.etf_dispersion_screener_project.config import RESULTS_DIR

dispersion_bp = Blueprint("dispersion", __name__, url_prefix="/dispersion")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _dates() -> List[str]:
    if not os.path.isdir(RESULTS_DIR):
        return []
    return sorted((d for d in os.listdir(RESULTS_DIR)
                   if DATE.match(d) and os.path.exists(os.path.join(RESULTS_DIR, d, "candidates.json"))), reverse=True)


def _selected_date() -> Optional[str]:
    wanted = request.args.get("date")
    dates = _dates()
    if wanted:
        if not DATE.match(wanted) or wanted not in dates:
            abort(404)
        return wanted
    return dates[0] if dates else None


def _load(day: str, name: str):
    with open(os.path.join(RESULTS_DIR, day, name), encoding="utf-8") as f:
        return json.load(f)


class _Row(dict):
    """A results row whose missing fields read as None: a file written before a field existed still renders."""

    def __missing__(self, key):
        return None


def _candidates(day: str) -> List[_Row]:
    rows = []
    for c in _load(day, "candidates.json"):
        row = _Row(c)
        row["constituent_legs"] = [_Row(leg) for leg in c.get("constituent_legs", [])]
        rows.append(row)
    return rows


def _manifest(day: str) -> dict:
    try:
        return _load(day, "run_manifest.json")
    except (OSError, ValueError):
        return {}


@dispersion_bp.route("/")
def results():
    day = _selected_date()
    if day is None:
        return render_template("dispersion_results.html", day=None, dates=[], candidates=[], counts={},
                               manifest={}), 200
    candidates = _candidates(day)
    counts = {}
    for c in candidates:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    try:
        universe_counts = _load(day, "universe.json").get("counts", {})
    except (OSError, ValueError):
        universe_counts = {}
    return render_template("dispersion_results.html", day=day, dates=_dates(), candidates=candidates,
                           counts=counts, universe_counts=universe_counts, manifest=_manifest(day))


@dispersion_bp.route("/etf/<ticker>")
def detail(ticker: str):
    day = _selected_date()
    if day is None:
        abort(404)
    candidate = next((c for c in _candidates(day) if c["etf"] == ticker.upper()), None)
    if candidate is None:
        abort(404)
    return render_template("dispersion_detail.html", day=day, c=candidate, manifest=_manifest(day))


@dispersion_bp.route("/api/candidates")
def api_candidates():
    day = _selected_date()
    return jsonify({"date": day, "candidates": _load(day, "candidates.json") if day else []})


@dispersion_bp.route("/api/candidates/<ticker>")
def api_candidate(ticker: str):
    day = _selected_date()
    candidate = next((c for c in (_load(day, "candidates.json") if day else []) if c["etf"] == ticker.upper()), None)
    if candidate is None:
        abort(404)
    return jsonify({"date": day, "candidate": candidate})
