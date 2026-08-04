from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_cox_ross_rubinstein_price_factor import CompanyShareOptionCoxRossRubinsteinPriceFactor


class CompanyShareOptionCoxRossRubinsteinPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionCoxRossRubinsteinPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionCoxRossRubinsteinPriceFactor) -> Optional[CompanyShareOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionCoxRossRubinsteinPriceFactor) -> Optional[CompanyShareOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionCoxRossRubinsteinPriceFactor]: ...
