from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor


class CompanyShareTransactionValueFactorPort(ABC):
    """Port interface for CompanyShareTransactionValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareTransactionValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareTransactionValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareTransactionValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareTransactionValueFactor) -> Optional[CompanyShareTransactionValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareTransactionValueFactor) -> Optional[CompanyShareTransactionValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareTransactionValueFactor]: ...
