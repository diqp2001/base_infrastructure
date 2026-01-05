from ibapi.contract import Contract

class IBKRIndexFutureRepository():

    def __init__(self, ibkr_client, local_repo: IndexFutureRepository):
        self.ibkr = ibkr_client
        self.local_repo = local_repo

    def get_or_create(self, symbol: str) -> IndexFuture:
        contract = self._fetch_contract(symbol)
        entity = self._contract_to_domain(contract)

        return self.local_repo.get_or_create(entity.symbol)
