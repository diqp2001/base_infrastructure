"""
Read-only contract tests against the real IB Gateway / TWS.

Opt-in: run only with IBKR_LIVE_SMOKE=1 (and IBKR_HOST, e.g. inside the app container).
Every order-sending method of the client is replaced by one that raises, so these tests can
only ask IBKR for contract definitions — they cannot place, modify, cancel or exercise anything.

What they check against IBKR itself (not against our own assumptions):
  * the stock contract the system should send for SPY resolves to exactly one instrument;
  * the stock and option contracts InteractiveBrokersBroker builds for an order resolve to them;
  * the strategy's OCC option symbol resolves, and IBKR's localSymbol for it is the key the
    position reconciler uses (instrument_key / normalize_ticker).
"""

import os
import threading
import unittest

from ibapi.contract import Contract

LIVE = os.getenv("IBKR_LIVE_SMOKE") == "1" and bool(os.getenv("IBKR_HOST"))
OPTION_OCC = "SPY   281215C00775000"          # SPX v2 config CompanyShareOption universe
SPY_CON_ID = 756733
BLOCKED = ("placeOrder", "cancelOrder", "reqGlobalCancel", "exerciseOptions", "reqIds",
           "reqAutoOpenOrders", "replaceFA")


def occ_contract(occ: str) -> Contract:
    """OCC 21-char symbol -> option Contract (root, yymmdd, C/P, strike * 1000)."""
    root, rest = occ[:6].strip(), occ[6:]
    contract = Contract()
    contract.symbol, contract.secType, contract.exchange, contract.currency = root, "OPT", "SMART", "USD"
    contract.lastTradeDateOrContractMonth = "20" + rest[:6]
    contract.right = rest[6]
    contract.strike = int(rest[7:]) / 1000
    contract.multiplier = "100"
    return contract


def stock_contract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol, contract.secType, contract.exchange, contract.currency = symbol, "STK", "SMART", "USD"
    return contract


@unittest.skipUnless(LIVE, "set IBKR_LIVE_SMOKE=1 (and IBKR_HOST) to query the real Gateway")
class LiveContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
        from src.application.services.misbuffet.brokers.ibkr.ibkr_settings import resolve_endpoint

        endpoint = resolve_endpoint("127.0.0.1", 7497, int(os.getenv("IBKR_SMOKE_CLIENT_ID", "94")))
        cls.client = client = IBTWSClient(endpoint.host, endpoint.port, endpoint.client_id)

        def refuse(name):
            def _blocked(*args, **kwargs):
                raise AssertionError(f"{name} called during a read-only test")
            return _blocked
        for name in BLOCKED:
            setattr(client, name, refuse(name))

        cls.done = {}
        cls.errors = {}
        original_end, original_error = client.contractDetailsEnd, client.error

        def details_end(req_id):
            original_end(req_id)
            cls.done.setdefault(req_id, threading.Event()).set()

        def error(req_id, code, message, *rest):
            original_error(req_id, code, message, *rest)
            if req_id in cls.done:                       # e.g. 200 "No security definition"
                cls.errors[req_id] = (code, message)
                cls.done[req_id].set()

        client.contractDetailsEnd, client.error = details_end, error
        if not client.connect_to_tws():
            raise unittest.SkipTest(f"no API handshake with {endpoint.host}:{endpoint.port} (Gateway logged in?)")
        cls.next_req = 9100

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect_from_tws()

    def details(self, contract, timeout=20):
        cls = type(self)
        cls.next_req += 1
        req = cls.next_req
        cls.done[req] = threading.Event()
        self.client.request_contract_details(req, contract)
        self.assertTrue(cls.done[req].wait(timeout), f"no contract details answer for {contract.symbol}")
        return self.client.contract_details.get(req, []), cls.errors.get(req)

    def test_order_methods_are_blocked(self):
        with self.assertRaises(AssertionError):
            self.client.placeOrder(1, stock_contract("SPY"), None)

    def test_spy_stock_resolves_to_one_instrument(self):
        found, error = self.details(stock_contract("SPY"))
        self.assertIsNone(error)
        self.assertEqual([(d["contract_id"], d["sec_type"], d["currency"]) for d in found],
                         [(SPY_CON_ID, "STK", "USD")])

    def broker_contract(self, ticker):
        """The contract InteractiveBrokersBroker builds for an order on `ticker` (nothing is sent)."""
        from types import SimpleNamespace
        from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
        broker = InteractiveBrokersBroker.__new__(InteractiveBrokersBroker)
        return broker._contract_for_order(SimpleNamespace(symbol=SimpleNamespace(value=ticker)))

    def test_contract_built_for_a_stock_order_is_the_stock(self):
        found, error = self.details(self.broker_contract("SPY"))
        self.assertIsNone(error)
        self.assertEqual([(d["contract_id"], d["sec_type"]) for d in found], [(SPY_CON_ID, "STK")])

    def test_contract_built_for_an_option_order_is_that_option(self):
        from src.application.services.misbuffet.algorithm.position_reconciler import normalize_ticker
        found, error = self.details(self.broker_contract(OPTION_OCC))
        self.assertIsNone(error, f"{OPTION_OCC}: {error}")
        self.assertEqual(len(found), 1, found)
        self.assertEqual(normalize_ticker(found[0]["local_symbol"]), normalize_ticker(OPTION_OCC))

    def test_strategy_option_resolves_and_matches_the_reconciler_key(self):
        from src.application.services.misbuffet.algorithm.position_reconciler import (
            instrument_key, normalize_ticker,
        )
        found, error = self.details(occ_contract(OPTION_OCC))
        self.assertIsNone(error, f"{OPTION_OCC} not resolved by IBKR: {error}")
        self.assertEqual(len(found), 1, found)
        option = found[0]
        self.assertEqual((option["sec_type"], option["symbol"]), ("OPT", "SPY"))
        self.assertEqual(normalize_ticker(option["local_symbol"]), normalize_ticker(OPTION_OCC))
        self.assertEqual(instrument_key(option["symbol"], option["local_symbol"], option["sec_type"]),
                         normalize_ticker(OPTION_OCC))


if __name__ == "__main__":
    unittest.main()
