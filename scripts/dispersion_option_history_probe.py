"""
READ-ONLY probe (no order code): which historical option bars does the IBKR gateway serve? Daily BID / ASK /
MIDPOINT / TRADES bars for a listed (unexpired) ATM option, and the same request for an expired one.
Historical bars are part of the market data the account already has (no snapshot, no per-request fee).

    python scripts/dispersion_option_history_probe.py SYMBOL EXPIRY(YYYYMMDD) STRIKE RIGHT [EXPIRED_EXPIRY]

Environment: PROBE_DURATION (default "6 M"), PROBE_BAR (default "1 day").
"""

import os
import sys
import time

from ibapi.contract import Contract

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

CLIENT_ID = 82                              # the probe's own client id


def option(symbol, expiry, strike, right):
    c = Contract()
    c.symbol, c.secType, c.exchange, c.currency = symbol, "OPT", "SMART", "USD"
    c.lastTradeDateOrContractMonth, c.strike, c.right, c.multiplier = expiry, float(strike), right, "100"
    c.includeExpired = True
    return c


DURATION, BAR = os.getenv("PROBE_DURATION", "6 M"), os.getenv("PROBE_BAR", "1 day")


def bars(client, req, contract, what):
    client.request_historical_data(req, contract, "", DURATION, BAR, what, use_rth=True, format_date=1)
    done = client.historical_data_done.get(req)
    finished = done is not None and done.wait(60)
    got = list(client.historical_data.get(req, []))
    error = client.historical_data_errors.get(req)
    return finished, got, error


def main():
    symbol, expiry, strike, right = sys.argv[1:5]
    expired = sys.argv[5] if len(sys.argv) > 5 else None
    ib = project_config.get_config()["ibkr"]
    client = IBTWSClient(ib["host"], int(ib["port"]), CLIENT_ID)
    if not client.connect_to_tws():
        raise SystemExit("gateway not available")
    time.sleep(2)
    req = 790_000
    try:
        for exp in [expiry] + ([expired] if expired else []):
            for what in ("BID", "ASK", "MIDPOINT", "TRADES"):
                req += 1
                finished, got, error = bars(client, req, option(symbol, exp, strike, right), what)
                first = got[0] if got else None
                last = got[-1] if got else None
                print(f"{symbol} {exp} {strike} {right} {what:8} finished={finished} bars={len(got)} "
                      f"first={first and (first['date'], first['close'])} last={last and (last['date'], last['close'])} "
                      f"error={error}", flush=True)
                time.sleep(2)                   # historical-data pacing
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
