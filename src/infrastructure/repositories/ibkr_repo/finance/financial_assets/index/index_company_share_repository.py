from src.domain.ports.finance.financial_assets.index.index_company_share_port import IndexCompanySharePort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.index_company_share_mapper import IndexCompanyShareMapper


class IBKRIndexCompanyShareRepository(IBKRIndexRepository, IndexCompanySharePort):
    """IBKR repository for equity indices (SPX, NDX, RUT, DJI, VIX, …)."""

    def __init__(self, ibkr_client, factory=None):
        self.ib_broker = ibkr_client
        self.factory = factory
        self.mapper = IndexCompanyShareMapper()
        self.local_repo = factory._local_repositories.get('IndexCompanyShare') if factory else None

    def _get_index_exchange(self, symbol: str) -> str:
        exchange_map = {
            'SPX':  'CBOE',
            'NDX':  'NASDAQ',
            'RUT':  'CBOE',
            'DJI':  'NYSE',
            'VIX':  'CBOE',
            'OEX':  'CBOE',
            'COMP': 'NASDAQ',
            'NYA':  'NYSE',
        }
        return exchange_map.get(symbol.upper(), 'CBOE')
