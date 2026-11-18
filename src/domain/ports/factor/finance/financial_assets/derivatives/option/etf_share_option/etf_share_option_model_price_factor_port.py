from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_model_price_factor import ETFShareOptionModelPriceFactor


class ETFShareOptionModelPriceFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ETFShareOptionModelPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ETFShareOptionModelPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ETFShareOptionModelPriceFactor]: ...

    @abstractmethod
    def add(self, entity: ETFShareOptionModelPriceFactor) -> Optional[ETFShareOptionModelPriceFactor]: ...

    @abstractmethod
    def update(self, entity: ETFShareOptionModelPriceFactor) -> Optional[ETFShareOptionModelPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ETFShareOptionModelPriceFactor]: ...
