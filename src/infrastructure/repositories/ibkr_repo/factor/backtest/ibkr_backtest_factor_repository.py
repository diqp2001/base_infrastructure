from typing import List, Optional

from src.domain.ports.factor.backtest.backtest_factor_port import BacktestFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.backtest.backtest_factor import BacktestFactor


class IBKRBacktestFactorRepository(BaseIBKRFactorRepository, BacktestFactorPort):
    """IBKR repository for BacktestFactor — all operations delegate to local repo."""

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory

    @property
    def entity_class(self):
        return BacktestFactor

    @property
    def local_repo(self):
        if self.factory:
            return self.factory._local_repositories.get('BacktestFactor')
        return None

    def get_by_id(self, id: int) -> Optional[BacktestFactor]:
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[BacktestFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[BacktestFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: BacktestFactor) -> Optional[BacktestFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: BacktestFactor) -> Optional[BacktestFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False

    def _create_or_get(self, name: str, **kwargs) -> Optional[BacktestFactor]:
        try:
            if self.local_repo:
                return self.local_repo._create_or_get(
                    entity_cls=BacktestFactor,
                    primary_key=name,
                    **kwargs,
                )
            return None
        except Exception as e:
            print(f"Error in IBKR _create_or_get for BacktestFactor '{name}': {e}")
            return None
