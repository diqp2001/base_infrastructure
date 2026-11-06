"""Read-only: dump every tick IBKR sends for one option (to see which carries open interest / volume).
    python scripts/dispersion_ibkr_ticks.py HOST PORT CLIENT_ID SYMBOL YYYYMMDD STRIKE GENERIC_TICKS"""
import sys
import time

from ibapi.contract import Contract

from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

host, port, cid, symbol, expiry, strike, generic = sys.argv[1:8]
client = IBTWSClient(host, int(port), int(cid))
client.connect_to_tws()
time.sleep(2)
client.request_market_data_type(2)
c = Contract()
c.symbol, c.secType, c.exchange, c.currency = symbol, "OPT", "SMART", "USD"
c.lastTradeDateOrContractMonth, c.strike, c.right, c.multiplier = expiry, float(strike), "C", "100"
client.request_market_data(9001, c, snapshot=False, generic_tick_list=generic)
time.sleep(12)
data = client.market_data.get(9001, {})
print("PRICES", data.get("prices"))
print("SIZES", data.get("sizes"))
print("GENERIC", data.get("generic"))
print("STRINGS", {k: v[:40] for k, v in data.get("strings", {}).items()})
print("OPTION TICKS", sorted(data.get("option", {})))
print("ERR", client.market_data_errors.get(9001), "TYPE", client.market_data_type.get(9001))
client.cancel_market_data(9001)
client.disconnect()
