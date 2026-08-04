from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_vpt_52w_20d_lag_factor import CompanyShareVpt52w20dLagFactor


class CompanyShareVpt52w20dLagFactorPort(ABC):
    """Port interface for CompanyShareVpt52w20dLagFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareVpt52w20dLagFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareVpt52w20dLagFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareVpt52w20dLagFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareVpt52w20dLagFactor) -> Optional[CompanyShareVpt52w20dLagFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareVpt52w20dLagFactor) -> Optional[CompanyShareVpt52w20dLagFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareVpt52w20dLagFactor]: ...
