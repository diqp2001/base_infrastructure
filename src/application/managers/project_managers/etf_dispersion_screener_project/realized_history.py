"""
6-month realized payoff history of the dispersion structure, for every eligible ETF of a screening date: a layer next
to the live screen (realized prices only - no option premium, no implied volatility). Started from the /dispersion
page (a background job) or by hand; READ-ONLY on IBKR (its own client id), no order code.

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.realized_history [YYYY-MM-DD]

Reads results/<date>/universe.json (eligible ETFs), every results/<d>/universe.json with d <= date (point-in-time
holdings), lookups.json (cached contract lookups); daily closes cached under results/.../price_history/.
Writes results/<date>/history/<TICKER>.json, history/summary.json and history/_status.json.
"""

import json
import os
import sys
import time
from datetime import date, datetime, time as clock_time, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_screener_project.maturities import NEW_YORK
from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
from src.application.services.dispersion.realized_dispersion_service import EtfHistory, RealizedDispersionService
from src.domain.entities.finance.dispersion.etf_holdings import ConstituentWeights
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable

STATUS = "_status.json"
CLOSE_FINAL = clock_time(16, 15)        # the day's daily bar is final after the close


def history_dir(results_dir: str, day: str) -> str:
    return os.path.join(results_dir, day, "history")


def write_status(results_dir: str, day: str, state: str, message: str = "") -> None:
    folder = history_dir(results_dir, day)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, STATUS), "w", encoding="utf-8") as f:
        json.dump({"state": state, "message": message, "at": datetime.now(timezone.utc).isoformat()}, f)


def read_status(results_dir: str, day: str) -> Optional[Dict[str, Any]]:
    try:
        with open(os.path.join(history_dir(results_dir, day), STATUS), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def last_completed_session(day: date, now: datetime) -> date:
    """The screening date itself once its daily bar is final; before that, the day before (no partial bar)."""
    local = now.astimezone(NEW_YORK)
    if day < local.date() or (day == local.date() and local.time() >= CLOSE_FINAL):
        return day
    return day - timedelta(days=1)


def snapshots_by_etf(results_dir: str, day: str) -> Dict[str, List[ConstituentWeights]]:
    """Every archived holdings snapshot (results/<d>/universe.json, d <= day) per ETF, one per holdings date."""
    out: Dict[str, Dict[date, ConstituentWeights]] = {}
    for d in sorted(x for x in os.listdir(results_dir) if len(x) == 10 and x <= day):
        try:
            with open(os.path.join(results_dir, d, "universe.json"), encoding="utf-8") as f:
                universe = json.load(f)
        except (OSError, ValueError):
            continue
        for e in universe.get("etfs", []):
            if e.get("status") != "eligible" or not e.get("weights") or not e.get("holdings_as_of"):
                continue
            as_of = date.fromisoformat(e["holdings_as_of"])
            out.setdefault(e["ticker"], {})[as_of] = ConstituentWeights(
                e["ticker"], as_of, e["weights"], e["equity_share"], [], e.get("holdings_source") or "")
    return {t: [snaps[k] for k in sorted(snaps)] for t, snaps in out.items()}


def history_row(h: EtfHistory) -> Dict[str, Any]:
    s = h.stats

    def r(x, n=4):
        return None if x is None else round(float(x), n)
    stats = None if s is None else {
        "as_of": str(s.as_of), "window_start": str(s.window_start), "n": s.n, "n_open": s.n_open,
        "n_incomplete": s.n_incomplete, "mean": r(s.mean, 2), "median": r(s.median, 2),
        "cumulative": r(s.cumulative, 2), "positive_rate": r(s.positive_rate),
        "normalized_mean": r(s.normalized_mean, 6), "normalized_median": r(s.normalized_median, 6),
        "normalized_cumulative": r(s.normalized_cumulative, 6),
        "normalized_positive_rate": r(s.normalized_positive_rate), "return_mean": r(s.return_mean),
        "etf_call_mean": r(s.etf_call_mean, 6), "basket_call_mean": r(s.basket_call_mean, 6),
        "replication_mean": r(s.replication_mean, 6), "replication_median": r(s.replication_median, 6),
        "replication_cumulative": r(s.replication_cumulative, 6),
        "replication_positive_rate": r(s.replication_positive_rate),
        "replication_negative_rate": r(s.replication_negative_rate),
        "problems": s.problems,
    }
    return {"etf": h.etf, "as_of": str(h.as_of), "membership": h.membership, "reasons": h.reasons, "stats": stats}


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def write_history(folder: str, h: EtfHistory) -> None:
    os.makedirs(folder, exist_ok=True)
    row = history_row(h)
    row["series"] = [[str(d), round(c, 2), round(n, 6)] for d, c, n in h.series]
    row["periods"] = {str(step): {
        "stats": {"n": st.n, "n_incomplete": st.n_incomplete, "etf_call_mean": _r(st.etf_call_mean),
                  "basket_call_mean": _r(st.basket_call_mean), "mean": _r(st.mean), "cumulative": _r(st.cumulative),
                  "positive_rate": _r(st.positive_rate, 4)},
        "periods": [{"start": str(p.start), "end": str(p.end),
                     "start_day": str(p.start_day) if p.start_day else None,
                     "end_day": str(p.end_day) if p.end_day else None, "etf_return": _r(p.etf_return),
                     "etf_call_return": _r(p.etf_call_return), "basket_call_return": _r(p.basket_call_return),
                     "replication_difference": _r(p.replication_difference),
                     "holdings_as_of": str(p.holdings_as_of) if p.holdings_as_of else None,
                     "point_in_time": p.point_in_time, "problem": p.problem} for p in periods],
    } for step, (periods, st) in h.periods.items()}
    row["replication_series"] = [[str(d), round(e, 6), round(b, 6), round(x, 6)] for d, e, b, x in h.replication_series]
    row["observations"] = [{
        "initiated": str(o.initiated), "expiry": str(o.expiry) if o.expiry else None, "dte": o.dte,
        "settled": str(o.settled) if o.settled else None, "etf_strike": o.etf_strike, "etf_settle": o.etf_settle,
        "etf_payoff": None if o.etf_payoff is None else round(o.etf_payoff, 2),
        "basket_payoff": None if o.basket_payoff is None else round(o.basket_payoff, 2),
        "dispersion_payoff": None if o.dispersion_payoff is None else round(o.dispersion_payoff, 2),
        "normalized": None if o.normalized is None else round(o.normalized, 6),
        "payoff_return": None if o.payoff_return is None else round(o.payoff_return, 4),
        "etf_return": None if o.etf_return is None else round(o.etf_return, 6),
        "etf_call_return": None if o.etf_call_return is None else round(o.etf_call_return, 6),
        "basket_call_return": None if o.basket_call_return is None else round(o.basket_call_return, 6),
        "replication_difference": None if o.replication_difference is None else round(o.replication_difference, 6),
        "holdings_as_of": str(o.holdings_as_of) if o.holdings_as_of else None, "point_in_time": o.point_in_time,
        "problem": o.problem,
    } for o in h.observations]
    with open(os.path.join(folder, f"{h.etf}.json"), "w", encoding="utf-8") as f:
        json.dump(row, f, indent=1)


def run(day: str, prices=None, resolver=None, config: Optional[Dict[str, Any]] = None, screen=None,
        tickers: Optional[List[str]] = None, now=lambda: datetime.now(timezone.utc)) -> Dict[str, Any]:
    config = config or project_config.get_config()
    results_dir = config["results_dir"]
    screen = screen or project_config.SCREEN
    folder = history_dir(results_dir, day)
    write_status(results_dir, day, "running")
    client = None
    try:
        as_of = last_completed_session(date.fromisoformat(day), now())
        snapshots = snapshots_by_etf(results_dir, day)
        with open(os.path.join(results_dir, day, "universe.json"), encoding="utf-8") as f:
            eligible = [e["ticker"] for e in json.load(f)["etfs"] if e["status"] == "eligible"]
        if tickers:
            eligible = [t for t in eligible if t in tickers]
        if prices is None or resolver is None:
            prices, resolver, client = _connect(config, results_dir, day)
        service = RealizedDispersionService(prices, resolver, screen)
        summary = {"as_of": str(as_of), "computed_at": now().isoformat(), "etfs": {}}
        for i, ticker in enumerate(eligible, 1):
            write_status(results_dir, day, "running", f"{ticker} ({i} of {len(eligible)})")
            try:
                h = service.history(ticker, snapshots.get(ticker, []), as_of, progress=lambda m: print(m, flush=True))
            except MarketDataUnavailable as e:
                h = EtfHistory(ticker, as_of, reasons=[f"market data unavailable: {e}"[:200]])
            write_history(folder, h)
            summary["etfs"][ticker] = history_row(h)
            if h.reasons:
                print(f"{ticker}: no history ({'; '.join(h.reasons)[:120]})", flush=True)
        with open(os.path.join(folder, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=1)
        done = sum(1 for e in summary["etfs"].values() if e["stats"] and e["stats"]["n"])
        write_status(results_dir, day, "done", f"{done} of {len(eligible)} ETFs with a history")
        return summary
    except Exception as e:
        write_status(results_dir, day, "failed", repr(e)[:300])
        raise
    finally:
        if client is not None:
            client.disconnect()


def _connect(config: Dict[str, Any], results_dir: str, day: str):
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.cached_price_history import CachedPriceHistory
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_option_market_data import (
        IBKROptionMarketData,
    )
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_price_history import IBKRPriceHistory
    ib = config["ibkr"]
    client = IBTWSClient(ib["host"], int(ib["port"]), int(ib["history_client_id"]))
    if not client.connect_to_tws():
        raise ConnectionError(f"IBKR {ib['host']}:{ib['port']} not available")
    time.sleep(2)
    md = IBKROptionMarketData(client, max_lines=int(ib.get("max_lines", 40)),
                              timeout_seconds=float(ib.get("timeout_seconds", 12.0)),
                              pause_seconds=float(ib.get("pause_seconds", 0.2)))
    screening = DispersionScreeningService(md, project_config.SCREEN)
    lookups = os.path.join(results_dir, day, "lookups.json")
    if os.path.exists(lookups):
        with open(lookups, encoding="utf-8") as f:
            screening.import_lookups(json.load(f), date.fromisoformat(day))
    prices = CachedPriceHistory(IBKRPriceHistory(client, pause_seconds=float(ib.get("history_pause_seconds", 1.5))),
                                config["price_history_dir"])
    # contract identity does not depend on the date: resolve as of today (the adapter serves current data only)
    return prices, (lambda symbols, _day: screening.resolve(symbols, date.today())), client


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat())
