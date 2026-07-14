"""
IBKR repository for CurrencyValueFactor — delegates to local repo.
"""

from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor
from src.domain.ports.factor.currency_value_factor_port import CurrencyValueFactorPort


class IBKRCurrencyValueFactorRepository(CurrencyValueFactorPort):
    """IBKR repository for CurrencyValueFactor — all ops delegate to local repo."""

    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = (
            factory._local_repositories.get('CurrencyValueFactor') if factory else None
        )

    @property
    def entity_class(self):
        return self.mapper.get_factor_entity() if self.local_repo else CurrencyValueFactor

    @property
    def model_class(self):
        return self.local_repo.get_factor_model() if self.local_repo else None

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyValueFactor]:
        if self.local_repo:
            return self.local_repo._create_or_get(entity_cls, primary_key, **kwargs)
        return None

    def get_by_id(self, id: int) -> Optional[CurrencyValueFactor]:
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CurrencyValueFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[CurrencyValueFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CurrencyValueFactor) -> Optional[CurrencyValueFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CurrencyValueFactor) -> Optional[CurrencyValueFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False
