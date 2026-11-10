"""
The per-ETF maturities view: the strategy priced at every expiry the ETF and all its constituents list, for one ETF
of a screening date. Started from the /dispersion page (a background job) or by hand; READ-ONLY on IBKR (its own
client id), no order code.

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.maturities TICKER [YYYY-MM-DD]

Reads results/<date>/universe.json (the ETF's holdings) and lookups.json (contract lookups of the screen), writes
results/<date>/maturities/<TICKER>.json and <TICKER>.status.json (starting / running / done / failed).
Every maturity is kept in the file; "complete" marks the ones with all the data (owner, 2026-11-06: the page shows
only those): a bid and an ask on the ETF call and on every constituent call, so the strategy and its reverse are
both priced.
"""

import json
import os
import sys
import time
from dataclasses import replace
from datetime import date, datetime, time as clock_time, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
    candidate_row, constituent_rows,
)
from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
from src.domain.ports.finance.dispersion.etf_holdings import ConstituentWeights

NEW_YORK = ZoneInfo("America/New_York")


def maturities_dir(results_dir: str, day: str) -> str:
    return os.path.join(results_dir, day, "maturities")


def write_status(results_dir: str, day: str, ticker: str, state: str, message: str = "") -> None:
    folder = maturities_dir(results_dir, day)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{ticker}.status.json"), "w", encoding="utf-8") as f:
        json.dump({"state": state, "message": message, "at": datetime.now(timezone.utc).isoformat()}, f)


def read_status(results_dir: str, day: str, ticker: str) -> Optional[Dict[str, Any]]:
    try:
        with open(os.path.join(maturities_dir(results_dir, day), f"{ticker}.status.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def market_open(now: datetime) -> bool:
    """Regular NYSE hours on a weekday (holidays: the quotes come back frozen and are labelled so)."""
    local = now.astimezone(NEW_YORK)
    return local.weekday() < 5 and clock_time(9, 30) <= local.time() < clock_time(16, 0)


def etf_weights(results_dir: str, day: str, ticker: str):
    with open(os.path.join(results_dir, day, "universe.json"), encoding="utf-8") as f:
        universe = json.load(f)
    row = next((e for e in universe["etfs"] if e["ticker"] == ticker and e["status"] == "eligible"), None)
    if row is None:
        raise ValueError(f"{ticker} is not an eligible ETF of the {day} universe")
    weights = ConstituentWeights(ticker, date.fromisoformat(row["holdings_as_of"]), row["weights"],
                                 row["equity_share"], [], row["holdings_source"] or "")
    return row["name"], weights


def run(ticker: str, day: str, market_data=None, config: Optional[Dict[str, Any]] = None, screen=None,
        now=lambda: datetime.now(timezone.utc)) -> dict:
    config = config or project_config.get_config()
    results_dir = config["results_dir"]
    screen = screen or project_config.SCREEN
    frozen = not market_open(now())
    if frozen:                                     # after the close: last (frozen) quotes, labelled as such
        screen = replace(screen, allow_frozen_quotes=True, max_quote_age_seconds=86_400.0)
    write_status(results_dir, day, ticker, "running", "frozen quotes (market closed)" if frozen else "live quotes")
    client = None
    try:
        name, weights = etf_weights(results_dir, day, ticker)
        if market_data is None:
            market_data, client = _connect(config)
        service = DispersionScreeningService(market_data, screen, now=now)
        lookups = os.path.join(results_dir, day, "lookups.json")
        if os.path.exists(lookups):
            with open(lookups, encoding="utf-8") as f:
                service.import_lookups(json.load(f), date.fromisoformat(day))
        candidates, reasons = service.maturities(ticker, name, weights, date.fromisoformat(day),
                                                 progress=lambda m: print(m, flush=True))
        result = {
            "etf": ticker, "name": name, "screening_date": day, "computed_at": now().isoformat(),
            "frozen_quotes": frozen, "reasons": reasons,
            "maturities": [_maturity_row(c) for c in candidates],
        }
        folder = maturities_dir(results_dir, day)
        with open(os.path.join(folder, f"{ticker}.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
        complete = sum(1 for m in result["maturities"] if m["complete"])
        write_status(results_dir, day, ticker, "done", f"{complete} of {len(candidates)} maturities with all the data")
        return result
    except Exception as e:
        write_status(results_dir, day, ticker, "failed", repr(e)[:300])
        raise
    finally:
        if client is not None:
            client.disconnect()


def _maturity_row(c) -> dict:
    row = {**candidate_row(c), "constituent_legs": constituent_rows(c)}
    row["complete"] = row["net_premium"] is not None and row["reverse_net_premium"] is not None
    return row


def _connect(config: Dict[str, Any]):
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_option_market_data import (
        IBKROptionMarketData,
    )
    ib = config["ibkr"]
    client = IBTWSClient(ib["host"], int(ib["port"]), int(ib["maturities_client_id"]))
    if not client.connect_to_tws():
        raise ConnectionError(f"IBKR {ib['host']}:{ib['port']} not available")
    time.sleep(2)
    md = IBKROptionMarketData(client, max_lines=int(ib.get("max_lines", 40)),
                              timeout_seconds=float(ib.get("timeout_seconds", 12.0)),
                              pause_seconds=float(ib.get("pause_seconds", 0.2)))
    return md, client


if __name__ == "__main__":
    ticker_arg = sys.argv[1].upper()
    day_arg = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
    run(ticker_arg, day_arg)
