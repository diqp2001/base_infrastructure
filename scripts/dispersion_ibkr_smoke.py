"""
Read-only check of the dispersion screener's IBKR option data (P.03): resolve shares, option chains, underlying and
option quotes with IBKR's model greeks. No order code is reachable from here.

    python scripts/dispersion_ibkr_smoke.py HOST PORT CLIENT_ID SYMBOL [SYMBOL ...]
"""

import sys
import time
from datetime import date

from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
from src.domain.ports.finance.dispersion.option_data import OptionContractSpec
from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_option_market_data import IBKROptionMarketData


def main(host, port, client_id, symbols):
    client = IBTWSClient(host, int(port), int(client_id))
    if not client.connect_to_tws():
        print("not connected")
        return 2
    time.sleep(2)
    try:
        today = date.today()
        md = IBKROptionMarketData(client, max_lines=20)
        resolved = md.resolve_underlyings(symbols, today)
        for s, u in resolved.items():
            print("RESOLVE", s, u and (u.con_id, u.primary_exchange, u.stock_type, u.long_name))
        underlyings = [u for u in resolved.values() if u]
        quotes = md.underlying_quotes(underlyings, today)
        specs = []
        for u in underlyings:
            q = quotes[u.symbol]
            print("QUOTE", u.symbol, q.quote.bid, q.quote.ask, q.quote.last, q.quote.close, "type",
                  q.quote.market_data_type, q.quote.error)
            chains = md.option_chains(u, today)
            for c in chains:
                print("CHAIN", u.symbol, c.trading_class, c.multiplier, len(c.expirations), "expiries",
                      [str(e) for e in c.expirations[:6]], len(c.strikes), "strikes")
            std = [c for c in chains if c.trading_class == u.symbol.replace(".", " ")] or chains
            if not std or q.price is None:
                continue
            chain = std[0]
            expiry = min(chain.expirations, key=lambda e: abs((e - today).days - 30))
            strike = min(chain.strikes, key=lambda k: abs(k / q.price - 1))
            specs.append(OptionContractSpec(u.symbol, expiry, strike, "C", chain.multiplier, chain.trading_class))
        for key, oq in md.option_quotes(specs, today).items():
            g = oq.greeks
            print("OPTION", key, "bid", oq.quote.bid, "ask", oq.quote.ask, "type", oq.quote.market_data_type,
                  "iv", g.implied_vol, "delta", g.delta, "gamma", g.gamma, "vega", g.vega, "theta", g.theta,
                  "und", g.underlying_price, "oi", oq.open_interest, "vol", oq.quote.volume, g.source,
                  oq.quote.error)
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]))
