"""
IBKR ETF Share Repository - Interactive Brokers implementation for ETF shares (e.g. DIA, SPY).

The IBKR side of the ETFShare entity, like IBKRCompanyShareRepository for company shares: an ETF trades as a stock
(secType STK, SMART routing), so its contract, contract details and historical bars are requested exactly as a
company share's. Persistence is delegated to the local ETFShareRepository. With this repository (and
IBKRETFShareFactorRepository) the Misbuffet MarketDataService imports an ETF's bars like any company share's.

(An earlier IBKR ETF share repository was removed with the old ETF share model on 2026-05-08; ETFShare came back for
the dispersion screener with local repositories only. Recreated 2026-11-16.)
"""

import os
from datetime import date
from typing import List, Optional

from ibapi.contract import Contract

from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare
from src.domain.ports.finance.financial_assets.share.etf_share.etf_share_port import ETFSharePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.financial_asset_repository import (
    IBKRFinancialAssetRepository,
)
from src.infrastructure.repositories.mappers.finance.financial_assets.share.etf_share.etf_share_mapper import (
    ETFShareMapper,
)


class IBKRETFShareRepository(IBKRFinancialAssetRepository, ETFSharePort):

    def __init__(self, ibkr_client, factory=None):
        self.ib_broker = ibkr_client
        self.factory = factory
        self.local_repo = self.factory.get_local_repository("ETFShare")
        self.mapper = ETFShareMapper()

    @property
    def entity_class(self):
        return ETFShare

    def _create_or_get(self, symbol: str = None, **kwargs) -> Optional[ETFShare]:
        """The stored ETF share for this ticker, else one built from IBKR's contract details."""
        try:
            existing = self.local_repo.get_by_symbol(symbol)
            if existing:
                return existing
            contract = self._fetch_contract(symbol)
            details = self._fetch_contract_details(contract) if contract else None
            if not details:
                return None
            d = details[0] if details else {}
            exchange = self._get_or_create_exchange(d.get("exchange") or contract.exchange)
            return self.local_repo._create_or_get(
                symbol, exchange_id=getattr(exchange, "id", None), currency=d.get("currency") or "USD",
                name=d.get("long_name") or symbol, asset_class=kwargs.get("asset_class", "equity"),
                start_date=kwargs.get("start_date") or date.today())
        except Exception as e:
            try:
                self.local_repo.session.rollback()
            except Exception:
                pass
            print(f"Error in IBKR _create_or_get for ETF share {symbol}: {e}")
            return None

    # -- IBKR contract --
    def _fetch_contract(self, symbol: str, **kwargs) -> Optional[Contract]:
        try:
            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"          # an ETF is a stock at IBKR
            contract.exchange = "SMART"
            contract.currency = "USD"
            return contract
        except Exception as e:
            print(f"Error fetching IBKR contract for ETF share {symbol}: {e}")
            return None

    def _fetch_historical_contract(self, symbol: str) -> Optional[Contract]:
        """STK contracts work for both reqContractDetails and reqHistoricalData."""
        return self._fetch_contract(symbol)

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        try:
            details = self.ib_broker.get_contract_details(contract, timeout=15)
            if details:
                return details
            print(f"No contract details received for ETF share {contract.symbol}")
            return None
        except Exception as e:
            print(f"Error fetching IBKR ETF share contract details: {e}_{os.path.abspath(__file__)}")
            return None

    def _get_or_create_exchange(self, exchange_code: str):
        try:
            repo = getattr(self.factory, "exchange_ibkr_repo", None) if self.factory else None
            return repo._create_or_get(exchange_code) if repo else None
        except Exception as e:
            print(f"Error getting or creating exchange {exchange_code}: {e}")
            return None

    # -- ETFSharePort (local) --
    def get_by_id(self, etf_share_id: int) -> Optional[ETFShare]:
        return self.local_repo.get_by_id(etf_share_id)

    def get_by_symbol(self, symbol: str) -> Optional[ETFShare]:
        return self.local_repo.get_by_symbol(symbol)

    def get_all(self) -> List[ETFShare]:
        return self.local_repo.get_all()

    def add(self, etf_share: ETFShare) -> ETFShare:
        return self.local_repo.add(etf_share)
