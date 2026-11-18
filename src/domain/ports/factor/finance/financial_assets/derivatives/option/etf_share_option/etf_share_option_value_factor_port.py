from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_value_factor import ETFShareOptionValueFactor


class ETFShareOptionValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ETFShareOptionValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ETFShareOptionValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ETFShareOptionValueFactor]: ...

    @abstractmethod
    def add(self, entity: ETFShareOptionValueFactor) -> Optional[ETFShareOptionValueFactor]: ...

    @abstractmethod
    def update(self, entity: ETFShareOptionValueFactor) -> Optional[ETFShareOptionValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ETFShareOptionValueFactor]: ...
