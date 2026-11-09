"""
The put version of the screen's trade, for one ETF of a screening date: short the ATM ETF put at the bid, long the
ATM constituent puts at the ask, sized like the calls (replicate(): the ETF's holdings), at the expiry the screen
chose for the calls. Same checks and premium rule as the screen (DispersionScreeningService with right="P").
Started from the ETF page (a background job) or by hand; READ-ONLY on IBKR (its own client id), no order code.

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.puts TICKER [YYYY-MM-DD]

Reads results/<date>/universe.json (holdings), candidates.json (the call trade's expiry) and lookups.json; writes
results/<date>/puts/<TICKER>.json and <TICKER>.status.json. The put quotes are the ones of the run (computed_at),
not of the screen: after the close they are the last (frozen) quotes, labelled so.
"""

import json
import os
import re
import sys
from dataclasses import replace
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_screener_project.maturities import (
    _connect as _connect_maturities, etf_weights, market_open,
)
from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
    candidate_row, constituent_rows,
)
from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService

CALL = re.compile(r"\bcall(s?)\b")


def puts_dir(results_dir: str, day: str) -> str:
    return os.path.join(results_dir, day, "puts")


def write_status(results_dir: str, day: str, ticker: str, state: str, message: str = "") -> None:
    folder = puts_dir(results_dir, day)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{ticker}.status.json"), "w", encoding="utf-8") as f:
        json.dump({"state": state, "message": message, "at": datetime.now(timezone.utc).isoformat()}, f)


def read_status(results_dir: str, day: str, ticker: str) -> Optional[Dict[str, Any]]:
    try:
        with open(os.path.join(puts_dir(results_dir, day), f"{ticker}.status.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def call_expiry(results_dir: str, day: str, ticker: str) -> Optional[date]:
    """The expiry the screen chose for the ETF's call trade (the put trade uses the same maturity)."""
    with open(os.path.join(results_dir, day, "candidates.json"), encoding="utf-8") as f:
        row = next((c for c in json.load(f) if c["etf"] == ticker), None)
    return date.fromisoformat(row["expiry"]) if row and row.get("expiry") else None


def _put_words(text: str) -> str:
    """The service's reasons speak of calls: in the put trade they are puts."""
    return CALL.sub(lambda m: "put" + m.group(1), text or "")


def put_row(c) -> dict:
    row = {**candidate_row(c), "constituent_legs": constituent_rows(c)}
    row["reasons"] = _put_words(row.get("reasons"))
    for leg in row["constituent_legs"]:
        leg["status"], leg["exceptions"] = _put_words(leg.get("status")), _put_words(leg.get("exceptions"))
    row["complete"] = row["net_premium"] is not None and row["reverse_net_premium"] is not None
    return row


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
        expiry = call_expiry(results_dir, day, ticker)
        if market_data is None:
            market_data, client = _connect(config)
        service = DispersionScreeningService(market_data, screen, now=now, right="P")
        lookups = os.path.join(results_dir, day, "lookups.json")
        if os.path.exists(lookups):
            with open(lookups, encoding="utf-8") as f:
                service.import_lookups(json.load(f), date.fromisoformat(day))
        # the screen's expiry rule picks the same maturity when the call trade has none (not screened that far)
        candidate = service.screen_etf(ticker, name, weights, date.fromisoformat(day), expiry=expiry)
        result = {"etf": ticker, "name": name, "screening_date": day, "computed_at": now().isoformat(),
                  "frozen_quotes": frozen, "trade": put_row(candidate)}
        with open(os.path.join(puts_dir(results_dir, day), f"{ticker}.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
        t = result["trade"]
        write_status(results_dir, day, ticker, "done",
                     f"net premium {t['net_premium']:,.2f}" if t["net_premium"] is not None else t["status"])
        return result
    except Exception as e:
        write_status(results_dir, day, ticker, "failed", repr(e)[:300])
        raise
    finally:
        if client is not None:
            client.disconnect()


def _connect(config: Dict[str, Any]):
    ib = dict(config["ibkr"])
    ib["maturities_client_id"] = ib["puts_client_id"]           # its own client id: may run beside nothing else
    return _connect_maturities({**config, "ibkr": ib})


if __name__ == "__main__":
    ticker_arg = sys.argv[1].upper()
    day_arg = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
    run(ticker_arg, day_arg)
