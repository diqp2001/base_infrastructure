"""
/dispersion — ETF dispersion-option screener results (P.08). Read-only views of the files a screening run writes
(results/etf_dispersion_screener/<date>/candidates.json, universe.json); screens are started outside the web app.
The one action: start the maturities job of one ETF (read-only on IBKR, one job at a time).

    /dispersion/                     latest run (or ?date=YYYY-MM-DD): ranked results table
    /dispersion/etf/<ticker>         detail of one candidate (ETF, constituents, trade, deltas, premiums)
    /dispersion/etf/<ticker>/maturities        the strategy at every common expiry (POST .../run starts the job)
    /dispersion/api/candidates       JSON (same ?date=)
    /dispersion/api/candidates/<etf> JSON of one candidate
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import List, Optional

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_screener_project.config import RESULTS_DIR
from src.application.managers.project_managers.etf_dispersion_screener_project import puts as put_job
from src.application.managers.project_managers.etf_dispersion_screener_project import realized_history
from src.application.managers.project_managers.etf_dispersion_screener_project.maturities import (
    maturities_dir, read_status, write_status,
)

MATURITIES_MODULE = "src.application.managers.project_managers.etf_dispersion_screener_project.maturities"
PUTS_MODULE = "src.application.managers.project_managers.etf_dispersion_screener_project.puts"
HISTORY_MODULE = "src.application.managers.project_managers.etf_dispersion_screener_project.realized_history"
JOB_STALE_SECONDS = 30 * 60          # a job still "running" after this is considered dead (the button works again)

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
    history = _history_summary(day)
    for c in candidates:
        entry = history.get("etfs", {}).get(c["etf"]) or {}
        c["history"] = _Row(entry.get("stats") or {})
        c["history_reasons"] = "; ".join(entry.get("reasons") or [])
    counts = {}
    for c in candidates:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    try:
        universe_counts = _load(day, "universe.json").get("counts", {})
    except (OSError, ValueError):
        universe_counts = {}
    status = realized_history.read_status(RESULTS_DIR, day)
    return render_template("dispersion_results.html", day=day, dates=_dates(), candidates=candidates,
                           counts=counts, universe_counts=universe_counts, manifest=_manifest(day),
                           history=history, history_status=status, history_running=_job_active(status),
                           busy=_any_job_active(day))


@dispersion_bp.route("/etf/<ticker>")
def detail(ticker: str):
    day = _selected_date()
    if day is None:
        abort(404)
    candidate = next((c for c in _candidates(day) if c["etf"] == ticker.upper()), None)
    if candidate is None:
        abort(404)
    try:
        history = _load(day, os.path.join("history", f"{ticker.upper()}.json"))
    except (OSError, ValueError):
        history = None
    chart = _history_chart(history) if history and history.get("series") else None
    replication_chart = _replication_chart(history) if history and history.get("replication_series") else None
    return render_template("dispersion_detail.html", day=day, c=candidate, manifest=_manifest(day),
                           history=history, hstats=_Row((history or {}).get("stats") or {}), chart=chart,
                           replication_chart=replication_chart,
                           ticket=order_ticket(candidate, request.args.get("calls", type=int)),
                           **_put_context(day, ticker.upper()))


def _put_context(day: str, ticker: str) -> dict:
    """The put version of the trade (puts/<TICKER>.json, written by the put job) and its job status."""
    try:
        result = _load(day, os.path.join("puts", f"{ticker}.json"))
        trade = _Row(result["trade"], constituent_legs=[_Row(x) for x in result["trade"].get("constituent_legs", [])])
    except (OSError, ValueError, KeyError):
        result, trade = None, None
    status = put_job.read_status(RESULTS_DIR, day, ticker)
    return {"puts": result, "put": trade, "put_status": status, "put_running": _job_active(status),
            "put_ticket": order_ticket(trade, request.args.get("puts", type=int)) if trade else None,
            "busy": _any_job_active(day)}


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


def _job_active(status: Optional[dict]) -> bool:
    if not status or status.get("state") not in ("starting", "running"):
        return False
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(status["at"])).total_seconds()
    return age < JOB_STALE_SECONDS


def _any_job_active(day: str) -> Optional[str]:
    """The job running for this date (one at a time: the gateway is shared): a maturities ETF or '6M history'."""
    if _job_active(realized_history.read_status(RESULTS_DIR, day)):
        return "6M history"
    for folder, read, label in ((maturities_dir(RESULTS_DIR, day), read_status, "{} maturities"),
                                (put_job.puts_dir(RESULTS_DIR, day), put_job.read_status, "{} puts")):
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if name.endswith(".status.json"):
                ticker = name[: -len(".status.json")]
                if _job_active(read(RESULTS_DIR, day, ticker)):
                    return label.format(ticker)
    return None


def _wsl_path(path: str) -> str:
    """A Windows path as WSL sees it: C:/x/y -> /mnt/c/x/y (the launcher runs the job script inside WSL)."""
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    return f"/mnt/{drive[0].lower()}{rest.replace(os.sep, '/')}" if drive else path


def _launch(log: str, module: str, *args: str) -> None:
    """Start a read-only job (module + args) through the configured launcher, detached from the web process."""
    cfg = project_config.get_config()
    convert = _wsl_path if cfg["job_launcher"][:1] == ["wsl"] else (lambda p: p)
    command = cfg["job_launcher"] + [convert(cfg["job_script"]), convert(log), module, *args]
    if sys.platform == "win32":
        flags = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        flags = {"start_new_session": True}
    subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **flags)


@dispersion_bp.route("/etf/<ticker>/maturities")
def maturities(ticker: str):
    day = _selected_date()
    if day is None:
        abort(404)
    ticker = ticker.upper()
    if not any(c["etf"] == ticker for c in _candidates(day)):
        abort(404)
    try:
        result = _load(day, os.path.join("maturities", f"{ticker}.json"))
        result["maturities"] = [_Row(m, constituent_legs=[_Row(x) for x in m.get("constituent_legs", [])])
                                for m in result.get("maturities", [])]
    except (OSError, ValueError):
        result = None
    status = read_status(RESULTS_DIR, day, ticker)
    return render_template("dispersion_maturities.html", day=day, ticker=ticker, result=result, status=status,
                           running=_job_active(status), busy=_any_job_active(day))


@dispersion_bp.route("/etf/<ticker>/puts/run", methods=["POST"])
def run_puts(ticker: str):
    day = request.form.get("date", "")
    if not DATE.match(day) or day not in _dates():
        abort(404)
    ticker = ticker.upper()
    if not any(c["etf"] == ticker for c in _candidates(day)):
        abort(404)
    if _any_job_active(day) is None:             # one job at a time: the gateway is shared
        put_job.write_status(RESULTS_DIR, day, ticker, "starting")
        _launch(os.path.join(put_job.puts_dir(RESULTS_DIR, day), f"{ticker}.log"), PUTS_MODULE, ticker, day)
    return redirect(url_for("dispersion.detail", ticker=ticker, date=day) + "#puts")


@dispersion_bp.route("/etf/<ticker>/maturities/run", methods=["POST"])
def run_maturities(ticker: str):
    day = request.form.get("date", "")
    if not DATE.match(day) or day not in _dates():
        abort(404)
    ticker = ticker.upper()
    if not any(c["etf"] == ticker for c in _candidates(day)):
        abort(404)
    if _any_job_active(day) is None:             # one job at a time: the gateway is shared
        write_status(RESULTS_DIR, day, ticker, "starting")
        _launch(os.path.join(maturities_dir(RESULTS_DIR, day), f"{ticker}.log"), MATURITIES_MODULE, ticker, day)
    return redirect(url_for("dispersion.maturities", ticker=ticker, date=day))


def order_ticket(c: dict, etf_calls: Optional[int] = None) -> Optional[dict]:
    """The screen's trade in whole contracts: short etf_calls ETF calls at the bid (default: the fewest that give every
    constituent at least one whole contract), long round(contracts per ETF call x etf_calls) of each constituent call
    at the ask. Quantities are rounded to the nearest contract, so the basket only approximates the holdings: the
    exact (fractional) quantity is shown next to it. Prices per share; one contract = multiplier shares."""
    n = etf_calls if etf_calls and etf_calls > 0 else c.get("whole_contract_etf_calls")
    if not n or c.get("etf_call_bid") is None:
        return None
    legs, cost, missing = [], 0.0, []
    for r in c.get("constituent_legs") or []:
        exact = (r.get("contracts") or 0.0) * n
        buy = round(exact)
        m = r.get("multiplier") or 100.0
        ask = r.get("call_ask")
        total = None if ask is None else buy * ask * m
        if total is None and buy:
            missing.append(r["ticker"])
        cost += total or 0.0
        legs.append({"ticker": r["ticker"], "weight": r.get("weight"), "strike": r.get("strike"),
                     "expiry": r.get("expiry"), "exact": exact, "buy": buy, "ask": ask,
                     "contract_price": None if ask is None else ask * m, "total": total})
    proceeds = n * c["etf_call_bid"] * 100.0
    return {"etf_calls": n, "default_calls": c.get("whole_contract_etf_calls"), "etf_bid": c["etf_call_bid"],
            "etf_contract_price": c["etf_call_bid"] * 100.0, "proceeds": proceeds, "legs": legs,
            "contracts": sum(x["buy"] for x in legs), "cost": None if missing else cost,
            "net": None if missing else proceeds - cost, "missing": missing}


def _history_summary(day: str) -> dict:
    try:
        return _load(day, os.path.join("history", "summary.json"))
    except (OSError, ValueError):
        return {}


def _history_chart(history: dict) -> str:
    """The cumulative basket-call minus ETF-call payoff of the window, by settlement day (PNG, base64)."""
    import base64
    import io
    from datetime import date as _date

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    days = [_date.fromisoformat(d) for d, _, _ in history["series"]]
    cumulative = [c for _, c, _ in history["series"]]
    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=110)
    ax.plot(days, cumulative, color="#1f6feb", linewidth=1.6)
    ax.axhline(0.0, color="#888888", linewidth=0.9, linestyle="--")
    ax.fill_between(days, cumulative, 0.0, where=[c >= 0 for c in cumulative], color="#3fb950", alpha=0.15)
    ax.fill_between(days, cumulative, 0.0, where=[c < 0 for c in cumulative], color="#f85149", alpha=0.15)
    ax.set_ylabel("cumulative payoff diff ($ per ETF call)")
    ax.set_xlabel("settlement day")
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _replication_chart(history: dict) -> str:
    """ETF call payoff, basket call payoff and basket - ETF (% of the start price) by observation date (PNG, base64):
    shows when the constituent calls paid more than the ETF call, and whether a few dates drive it."""
    import base64
    import io
    from datetime import date as _date

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = history["replication_series"]
    days = [_date.fromisoformat(r[0]) for r in rows]
    etf, basket, diff = ([r[k] * 100 for r in rows] for k in (1, 2, 3))
    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=110)
    ax.bar(days, diff, width=1.0, color=["#3fb950" if v >= 0 else "#f85149" for v in diff], alpha=0.55,
           label="basket - ETF")
    ax.plot(days, etf, color="#8b949e", linewidth=1.1, label="ETF call payoff")
    ax.plot(days, basket, color="#1f6feb", linewidth=1.1, label="basket call payoff")
    ax.axhline(0.0, color="#444444", linewidth=0.9, linestyle="--")
    ax.set_ylabel("% of the start price")
    ax.set_xlabel("observation date (holding period start)")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@dispersion_bp.route("/history/run", methods=["POST"])
def run_history():
    """Start the 6M realized payoff job for every eligible ETF of the date (read-only, one job at a time)."""
    day = request.form.get("date", "")
    if not DATE.match(day) or day not in _dates():
        abort(404)
    if _any_job_active(day) is None:
        realized_history.write_status(RESULTS_DIR, day, "starting")
        _launch(os.path.join(realized_history.history_dir(RESULTS_DIR, day), "history.log"), HISTORY_MODULE, day)
    return redirect(url_for("dispersion.results", date=day))
