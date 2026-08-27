import os

from src.domain.ports.finance.financial_assets.index.index_bond_port import IndexBondPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.index_bond_mapper import IndexBondMapper


class IBKRIndexBondRepository(IBKRIndexRepository, IndexBondPort):
    """IBKR repository for bond / rate indices (SOFR3, SOFR1, USB, TNX, …)."""

    def __init__(self, ibkr_client, factory=None):
        self.ib_broker = ibkr_client
        self.factory = factory
        self.mapper = IndexBondMapper()
        self.local_repo = factory._local_repositories.get('IndexBond') if factory else None

    def _get_index_exchange(self, symbol: str) -> str:
        exchange_map = {
            'SOFR3': 'CME',
            'SOFR1': 'CME',
            'USB':   'CBOE',
            'TNX':   'CBOE',
            'FVX':   'CBOE',
            'IRX':   'CBOE',
        }
        return exchange_map.get(symbol.upper(), 'CME')
    
    def _fetch_contract(self, symbol: str, **kwargs):
        from ibapi.contract import Contract
        exchange = self._get_index_exchange(symbol)
        contract = Contract()
        contract.symbol = symbol.upper()
        contract.secType = "IND"
        contract.exchange = exchange
        contract.primaryExchange = exchange
        contract.currency = kwargs.get('currency', 'USD')
        return contract

    def _fetch_historical_contract(self, symbol: str):
        """Contract for reqHistoricalData: resolved via conId.

        IND contracts return a single detail result (no expiry chain), so we
        take contract_details_list[0] directly instead of filtering by local_symbol.
        """
        from ibapi.contract import Contract
        try:
            details_contract = self._fetch_contract(symbol)
            contract_details_list = self._fetch_contract_details(details_contract)
            if not contract_details_list:
                return None
            detail = contract_details_list[0]
            con_id = detail.get('contract_id')
            if not con_id:
                return None
            contract = Contract()
            contract.conId = con_id
            contract.exchange = detail.get('exchange', self._get_index_exchange(symbol))
            return contract
        except Exception as e:
            print(f"Error building historical IBKR contract for index bond {symbol}: {e}")
            return None

    def _create_or_get(self, symbol: str = None, **kwargs):
        try:
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing

            contract = self._fetch_contract(symbol, **kwargs)
            if not contract:
                return None

            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None

            entity = self._contract_to_domain(contract, contract_details_list)
            if not entity:
                return None

            return self.local_repo.add(entity)

        except Exception as e:
            print(f"Error in IBKRIndexBondRepository._create_or_get for {symbol}: {e}_{os.path.abspath(__file__)}")
            return None