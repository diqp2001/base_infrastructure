from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.index.index_bond_port import IndexBondPort
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.infrastructure.repositories.mappers.finance.financial_assets.index_bond_mapper import IndexBondMapper


class IndexBondRepository(IndexRepository, IndexBondPort):
    """Local repository for bond / rate indices (SOFR3, SOFR1, USB, TNX, …)."""

    def __init__(self, session: Session, factory):
        super().__init__(session, factory, mapper=IndexBondMapper())
