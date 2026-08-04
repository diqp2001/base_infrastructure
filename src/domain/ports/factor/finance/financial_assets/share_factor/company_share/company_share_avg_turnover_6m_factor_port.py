from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_avg_turnover_6m_factor import CompanyShareAvgTurnover6mFactor


class CompanyShareAvgTurnover6mFactorPort(ABC):
    """Port interface for CompanyShareAvgTurnover6mFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareAvgTurnover6mFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareAvgTurnover6mFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareAvgTurnover6mFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareAvgTurnover6mFactor) -> Optional[CompanyShareAvgTurnover6mFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareAvgTurnover6mFactor) -> Optional[CompanyShareAvgTurnover6mFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareAvgTurnover6mFactor]: ...
