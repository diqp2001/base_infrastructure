from . import IBTWSClient
from ibapi.contract import Contract
import time
import threading
from datetime import datetime


class ContractResolver:
    def __init__(self, ib: IBTWSClient):
        self.ib = ib

    def resolve_front_month(self, contract: Contract, timeout=5) -> Contract:
        req_id = abs(hash(f"cd_{contract.symbol}_{time.time()}")) % 10_000
        #self.ib.contract_details.pop(req_id, None)
        #self.ib._events[req_id] = threading.Event()

        self.ib.request_contract_details(req_id, contract)

        

        contracts = self.ib.contract_details[req_id]
        today = datetime.utcnow().strftime("%Y%m%d")

        return min(
            (c for c in contracts if c.lastTradeDateOrContractMonth >= today),
            key=lambda c: c.lastTradeDateOrContractMonth,
        )
