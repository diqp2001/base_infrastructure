from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.index.index_company_share_portfolio_port import IndexCompanySharePortfolioPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.index_company_share_portfolio_mapper import IndexCompanySharePortfolioMapper


class IndexCompanySharePortfolioRepository(IndexRepository, IndexCompanySharePortfolioPort):
    """Local repository for basket / portfolio indices."""

    def __init__(self, session: Session, factory):
        super().__init__(session, factory, mapper=IndexCompanySharePortfolioMapper())
