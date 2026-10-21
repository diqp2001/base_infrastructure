"""
IBKR historical-data diagnostic: the same qualified contract requested with several whatToShow types, one request
at a time, through the production request path (InteractiveBrokersBroker.request_history: pacing, unique request
ids, completion / error / timeout classification). READ-ONLY: every order-sending method of the client raises.

    python -m src.application.services.misbuffet.brokers.ibkr.history_diagnostics MSFT
    python -m src.application.services.misbuffet.brokers.ibkr.history_diagnostics MSFT --types TRADES MIDPOINT \\
        --bar "8 hours" --duration "3 D" --client-id 97

Options and futures: --sec-type OPT "SPY   281215C00775000" (OCC symbol), --sec-type FUT SR3Z6 --exchange CME;
--end "2026-08-06 16:00" (naive US/Eastern) to probe a past window.

Host / port come from ibkr_settings (IBKR_HOST / IBKR_PORT, default 127.0.0.1:7497). The end time is now (US/Eastern).
"""

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from ibapi.contract import Contract

ORDER_METHODS = ("placeOrder", "cancelOrder", "reqGlobalCancel", "exerciseOptions", "reqAutoOpenOrders")
DEFAULT_TYPES = ("TRADES", "MIDPOINT", "BID", "ASK")


@dataclass
class DiagnosticRow:
    what_to_show: str
    use_rth: bool
    duration: str
    bar_size: str
    end: str
    req_id: Optional[int]
    status: str
    failure: Optional[str]
    bars: int
    first_bar: str
    last_bar: str
    error_code: Optional[int]
    error_message: str
    elapsed: float

    def line(self) -> str:
        span = f"{self.first_bar} .. {self.last_bar}" if self.bars else "-"
        err = f"{self.error_code}: {self.error_message}" if self.error_code is not None else ""
        return (f"{self.what_to_show:9} RTH={str(self.use_rth):5} req={self.req_id} {self.status:9} "
                f"{(self.failure or ''):11} bars={self.bars:3} {span:37} {self.elapsed:5.1f}s {err}")


def stock(symbol: str, exchange: str = "SMART", currency: str = "USD", primary_exchange: str = "") -> Contract:
    contract = Contract()
    contract.symbol, contract.secType, contract.exchange, contract.currency = symbol, "STK", exchange, currency
    if primary_exchange:
        contract.primaryExchange = primary_exchange
    return contract


def option_from_occ(occ: str, exchange: str = "SMART", currency: str = "USD") -> Contract:
    """OCC 21-character symbol (root padded to 6, yymmdd, C/P, strike x 1000) -> option contract."""
    contract = Contract()
    contract.symbol, contract.secType, contract.exchange, contract.currency = occ[:6].strip(), "OPT", exchange, currency
    contract.lastTradeDateOrContractMonth = "20" + occ[6:12]
    contract.right = occ[12]
    contract.strike = int(occ[13:]) / 1000
    contract.multiplier = "100"
    return contract


def future_by_local_symbol(local_symbol: str, exchange: str, currency: str = "USD") -> Contract:
    contract = Contract()
    contract.localSymbol, contract.secType, contract.exchange, contract.currency = local_symbol, "FUT", exchange, currency
    return contract


def block_orders(client) -> None:
    def refuse(name):
        def _blocked(*args, **kwargs):
            raise RuntimeError(f"{name} refused: the history diagnostic is read-only")
        return _blocked
    for name in ORDER_METHODS:
        setattr(client, name, refuse(name))


def qualify(broker, contract: Contract) -> Dict:
    """IBKR's definition of the contract (conId, primary exchange, valid exchanges); the contract gets its conId."""
    details = broker.get_contract_details(contract)
    if len(details) != 1:
        return {"error": f"{len(details)} contract definitions returned", "details": details}
    d = details[0]
    contract.conId = d["contract_id"]
    if d.get("primary_exchange"):
        contract.primaryExchange = d["primary_exchange"]
    return d


def run_matrix(broker, contract: Contract, types: Sequence[str] = DEFAULT_TYPES, rth: Sequence[bool] = (True, False),
               duration: str = "3 D", bar_size: str = "1 day", timeout: int = 60,
               end: Optional[datetime] = None) -> List[DiagnosticRow]:
    """Each (whatToShow, useRTH) requested independently, sequentially, with a unique request id. `end`: naive
    US/Eastern time (default now)."""
    end_local = end or datetime.now(ZoneInfo("US/Eastern")).replace(tzinfo=None)
    end = broker.format_ib_datetime(date_time=end_local, duration=duration)
    rows = []
    for use_rth in rth:
        for what in types:
            r = broker.request_history(contract, end, duration, bar_size, what, use_rth=use_rth, timeout=timeout)
            dates = [str(b.get("date")) for b in r.bars]
            rows.append(DiagnosticRow(what, use_rth, duration, bar_size, end, r.req_id, r.status, r.failure,
                                      len(r.bars), dates[0] if dates else "", dates[-1] if dates else "",
                                      r.error_code, r.error_message, round(r.elapsed, 2)))
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="IBKR historical whatToShow diagnostic (read-only)")
    parser.add_argument("symbol")
    parser.add_argument("--types", nargs="+", default=list(DEFAULT_TYPES))
    parser.add_argument("--duration", default="3 D")
    parser.add_argument("--bar", default="1 day")
    parser.add_argument("--client-id", type=int, default=97)
    parser.add_argument("--rth", choices=["both", "true", "false"], default="both")
    parser.add_argument("--sec-type", choices=["STK", "OPT", "FUT"], default="STK")
    parser.add_argument("--exchange", default="SMART")
    parser.add_argument("--end", help='naive US/Eastern end time, e.g. "2026-08-06 16:00" (default now)')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
    broker = InteractiveBrokersBroker({"host": "127.0.0.1", "port": 7497, "client_id": args.client_id})
    if not broker.connect():
        print(f"could not connect to TWS / Gateway at {broker.host}:{broker.port} (client {broker.client_id})")
        return 2
    try:
        block_orders(broker.ib_connection)
        contract = (option_from_occ(args.symbol, args.exchange) if args.sec_type == "OPT" else
                    future_by_local_symbol(args.symbol, args.exchange) if args.sec_type == "FUT" else
                    stock(args.symbol, args.exchange))
        details = qualify(broker, contract)
        print(f"contract: {details}")
        rth = {"both": (True, False), "true": (True,), "false": (False,)}[args.rth]
        end = datetime.strptime(args.end, "%Y-%m-%d %H:%M") if args.end else None
        for row in run_matrix(broker, contract, args.types, rth, args.duration, args.bar, end=end):
            print(row.line())
    finally:
        broker.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
