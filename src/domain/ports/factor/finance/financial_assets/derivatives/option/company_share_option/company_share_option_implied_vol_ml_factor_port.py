from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import (
    CompanyShareOptionImpliedVolMlFactor,
)


class CompanyShareOptionImpliedVolMlFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        pass

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionImpliedVolMlFactor]:
        pass

    @abstractmethod
    def add(self, entity: CompanyShareOptionImpliedVolMlFactor) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        pass

    @abstractmethod
    def update(self, entity: CompanyShareOptionImpliedVolMlFactor) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        pass
