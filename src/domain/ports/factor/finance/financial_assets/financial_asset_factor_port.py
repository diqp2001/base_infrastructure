from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor


class FinancialAssetFactorPort(ABC):
    """Port interface for FinancialAssetFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FinancialAssetFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FinancialAssetFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[FinancialAssetFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FinancialAssetFactor]: ...

    @abstractmethod
    def add(self, entity: FinancialAssetFactor) -> Optional[FinancialAssetFactor]: ...

    @abstractmethod
    def update(self, entity: FinancialAssetFactor) -> Optional[FinancialAssetFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FinancialAssetFactor]: ...
