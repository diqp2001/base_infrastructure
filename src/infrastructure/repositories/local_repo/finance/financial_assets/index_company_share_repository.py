from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.index.index_company_share_port import IndexCompanySharePort
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.index_company_share_mapper import IndexCompanyShareMapper


class IndexCompanyShareRepository(IndexRepository, IndexCompanySharePort):
    """Local repository for equity indices (SPX, NDX, RUT, …)."""

    def __init__(self, session: Session, factory):
        super().__init__(session, factory, mapper=IndexCompanyShareMapper())
