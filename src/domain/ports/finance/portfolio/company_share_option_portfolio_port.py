from typing import List, Optional
from src.domain.entities.finance.portfolio.company_share_option_portfolio import CompanyShareOptionPortfolio
from abc import ABC, abstractmethod

class CompanyShareOptionPortfolioPort(ABC):
    """Port interface for PortfolioCompanyShare entity operations following repository pattern."""
    # def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolio]:
    #     pass

    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolio]:
    #     pass

    # def get_all(self) -> List[CompanyShareOptionPortfolio]:
    #     pass

    # def add(self, entity: CompanyShareOptionPortfolio) -> Optional[CompanyShareOptionPortfolio]:
    #     pass

    # def update(self, entity: CompanyShareOptionPortfolio) -> Optional[CompanyShareOptionPortfolio]:
    #     pass

    # def delete(self, id: int) -> bool:
    #     pass