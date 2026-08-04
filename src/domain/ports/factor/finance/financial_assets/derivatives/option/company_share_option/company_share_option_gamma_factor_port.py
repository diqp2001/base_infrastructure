from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import CompanyShareOptionGammaFactor


class CompanyShareOptionGammaFactorPort(ABC):
    """Port interface for CompanyShareOptionGammaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionGammaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionGammaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionGammaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionGammaFactor) -> Optional[CompanyShareOptionGammaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionGammaFactor) -> Optional[CompanyShareOptionGammaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionGammaFactor]: ...
