"""
IBKR Currency Factor Repository - Interactive Brokers implementation for CurrencyFactor entities.
"""

from typing import Optional, List, Dict, Any
from src.domain.ports.factor.currency_factor_port import CurrencyFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.currency_factor import CurrencyFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRCurrencyFactorRepository(BaseIBKRFactorRepository, CurrencyFactorPort):
    """IBKR implementation of CurrencyFactorPort."""

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return CurrencyFactor

    @property
    def local_repo(self):
        if self.factory:
            return self.factory._local_repositories.get('currency_factor')
        return None

    def get_by_id(self, entity_id: int) -> Optional[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: CurrencyFactor) -> Optional[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[CurrencyFactor]:
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create(self, name: str, group: str = "forex", subgroup: str = "currency") -> Optional[CurrencyFactor]:
        try:
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            new_factor = CurrencyFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Currency factor: {name} (from IBKR data)"
            )
            
            if self.local_repo:
                return self.local_repo.add(new_factor)
            return None
        except Exception as e:
            print(f"Error in get_or_create for currency factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        try:
            if 'rate' in ibkr_data:
                return float(ibkr_data['rate'])
            elif 'lastPrice' in ibkr_data:
                return float(ibkr_data['lastPrice'])
            elif 'bid' in ibkr_data:
                return float(ibkr_data['bid'])
            elif 'ask' in ibkr_data:
                return float(ibkr_data['ask'])
            return None
        except (ValueError, TypeError) as e:
            print(f"Error converting currency factor value: {e}")
            return None