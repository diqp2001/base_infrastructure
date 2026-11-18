"""
IBKR ETF Share Option Factor Repository - the raw IBKR series of an option on an ETF share (open / high / low / close
of a whatToShow, e.g. MIDPOINT): the MarketDataService creates these factors before asking IBKR for the option's bars.
Persistence is delegated to the local ETFShareOptionFactorRepository.
"""

from src.domain.ports.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor_port import (
    ETFShareOptionFactorPort,
)
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.share.etf_share.ibkr_etf_share_factor_repository import (
    IBKRETFShareFactorRepository,
)
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor_mapper import (
    ETFShareOptionFactorMapper,
)


class IBKRETFShareOptionFactorRepository(IBKRETFShareFactorRepository, ETFShareOptionFactorPort):

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client, factory)
        self.mapper = ETFShareOptionFactorMapper()

    @property
    def local_repo(self):
        return self.factory.get_local_repository("ETFShareOptionFactor") if self.factory else None
