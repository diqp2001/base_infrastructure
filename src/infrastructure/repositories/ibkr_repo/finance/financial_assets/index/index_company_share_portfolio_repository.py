from src.domain.ports.finance.financial_assets.index.index_company_share_portfolio_port import IndexCompanySharePortfolioPort
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.index_company_share_portfolio_mapper import IndexCompanySharePortfolioMapper


class IBKRIndexCompanySharePortfolioRepository(IBKRIndexRepository, IndexCompanySharePortfolioPort):
    """IBKR repository for basket / portfolio indices."""

    def __init__(self, ibkr_client, factory=None):
        self.ib_broker = ibkr_client
        self.factory = factory
        self.mapper = IndexCompanySharePortfolioMapper()
        self.local_repo = factory._local_repositories.get('IndexCompanySharePortfolio') if factory else None

    def _get_index_exchange(self, symbol: str) -> str:
        exchange_map = {
            'SPX':  'CBOE',
            'NDX':  'NASDAQ',
            'RUT':  'CBOE',
            'DJI':  'NYSE',
            'OEX':  'CBOE',
            'COMP': 'NASDAQ',
            'NYA':  'NYSE',
        }
        return exchange_map.get(symbol.upper(), 'CBOE')
