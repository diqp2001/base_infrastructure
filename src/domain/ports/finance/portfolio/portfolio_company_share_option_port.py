from typing import List, Optional
from src.domain.entities.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOption


class PortfolioCompanyShareOptionPort:

    def get_by_id(self, id: int) -> Optional[PortfolioCompanyShareOption]:
        pass

    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOption]:
        pass

    def get_all(self) -> List[PortfolioCompanyShareOption]:
        pass

    def add(self, entity: PortfolioCompanyShareOption) -> Optional[PortfolioCompanyShareOption]:
        pass

    def update(self, entity: PortfolioCompanyShareOption) -> Optional[PortfolioCompanyShareOption]:
        pass

    def delete(self, id: int) -> bool:
        pass