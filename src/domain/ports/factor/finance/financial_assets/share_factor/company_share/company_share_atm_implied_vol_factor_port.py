from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_atm_implied_vol_factor import CompanyShareATMImpliedVolFactor


class CompanyShareATMImpliedVolFactorPort(ABC):
    """Port interface for CompanyShareATMImpliedVolFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareATMImpliedVolFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareATMImpliedVolFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareATMImpliedVolFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareATMImpliedVolFactor) -> Optional[CompanyShareATMImpliedVolFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareATMImpliedVolFactor) -> Optional[CompanyShareATMImpliedVolFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareATMImpliedVolFactor]: ...
