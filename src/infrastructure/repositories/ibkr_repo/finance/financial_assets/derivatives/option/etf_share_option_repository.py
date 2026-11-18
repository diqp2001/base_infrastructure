"""
IBKR ETF Share Option Repository - options on an ETF share (e.g. DIA calls), the IBKR side of ETFShareOption.

An ETF option is an OPT contract on the ETF's symbol at IBKR, built exactly as a company share option's (OCC
symbol -> strike / expiry / right): this repository reuses IBKRCompanyShareOptionRepository's contract handling and
differs only in the entity it stores (ETFShareOption, local ETFShareOptionRepository) and its underlying (the
ETFShare, through IBKRETFShareRepository). With it the MarketDataService can ask IBKR for an ETF option's bars
(IBKR keeps no history of expired options: those requests return nothing, and the value falls back to the model
price - ETFShareOptionValueFactor).
"""

from typing import List, Optional

from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
from src.domain.ports.finance.financial_assets.derivatives.option.etf_share_option_port import ETFShareOptionPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.derivatives.option.company_share_option_repository import (
    IBKRCompanyShareOptionRepository,
)
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.etf_share_option_mapper import (
    ETFShareOptionMapper,
)


class IBKRETFShareOptionRepository(IBKRCompanyShareOptionRepository, ETFShareOptionPort):

    def __init__(self, ibkr_client, factory=None):
        self.ib_broker = ibkr_client
        self.factory = factory
        self.local_repo = self.factory.get_local_repository("ETFShareOption")
        self.mapper = ETFShareOptionMapper()

    @property
    def entity_class(self):
        return ETFShareOption

    def _get_or_create_underlying_company_share(self, symbol: str):
        """The option's underlying: the ETF share (IBKRETFShareRepository)."""
        try:
            repo = self.factory.get_ibkr_repository("ETFShare") if self.factory else None
            return repo._create_or_get(symbol) if repo else None
        except Exception as e:
            print(f"Error getting or creating ETF share {symbol}: {e}")
            return None

    # -- ETFShareOptionPort (local) --
    def get_by_underlying_id(self, underlying_asset_id: int) -> List[ETFShareOption]:
        return self.local_repo.get_by_underlying_id(underlying_asset_id)

    def get_by_id(self, option_id: int) -> Optional[ETFShareOption]:
        return self.local_repo.get_by_id(option_id)

    def get_by_symbol(self, symbol: str) -> Optional[ETFShareOption]:
        return self.local_repo.get_by_symbol(symbol)

    def get_all(self) -> List[ETFShareOption]:
        return self.local_repo.get_all()

    def add(self, entity: ETFShareOption) -> Optional[ETFShareOption]:
        return self.local_repo.add(entity)
