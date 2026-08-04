from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_bates_price_factor import CompanyShareOptionPortfolioBatesPriceFactor


class CompanyShareOptionPortfolioBatesPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionPortfolioBatesPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioBatesPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioBatesPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioBatesPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioBatesPriceFactor) -> Optional[CompanyShareOptionPortfolioBatesPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioBatesPriceFactor) -> Optional[CompanyShareOptionPortfolioBatesPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioBatesPriceFactor]: ...
