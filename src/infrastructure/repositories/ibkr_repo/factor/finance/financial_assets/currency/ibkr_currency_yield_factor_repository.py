"""
IBKR repository for CurrencyYieldFactor — delegates to local repo.
"""

from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import CurrencyYieldFactor
from src.domain.ports.factor.finance.financial_assets.currency.currency_yield_factor_port import CurrencyYieldFactorPort


class IBKRCurrencyYieldFactorRepository(CurrencyYieldFactorPort):
    """IBKR repository for CurrencyYieldFactor — all ops delegate to local repo."""

    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = (
            factory._local_repositories.get('CurrencyYieldFactor') if factory else None
        )

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity() if self.local_repo else CurrencyYieldFactor

    @property
    def model_class(self):
        return self.local_repo.get_factor_model() if self.local_repo else None

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyYieldFactor]:
        if self.local_repo:
            return self.local_repo._create_or_get(entity_cls, primary_key, **kwargs)
        return None

    def get_by_id(self, id: int) -> Optional[CurrencyYieldFactor]:
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CurrencyYieldFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[CurrencyYieldFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CurrencyYieldFactor) -> Optional[CurrencyYieldFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CurrencyYieldFactor) -> Optional[CurrencyYieldFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False
