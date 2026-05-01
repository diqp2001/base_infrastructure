from typing import List, Optional
from src.domain.entities.finance.holding.company_share_option_portfolio_holding import PortfolioCompanyShareOptionHolding


class PortfolioCompanyShareOptionHoldingPort:

    def get_by_id(self, id: int) -> Optional[PortfolioCompanyShareOptionHolding]:
        pass

    def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioCompanyShareOptionHolding]:
        pass

    def get_all(self) -> List[PortfolioCompanyShareOptionHolding]:
        pass

    def add(self, entity: PortfolioCompanyShareOptionHolding) -> Optional[PortfolioCompanyShareOptionHolding]:
        pass

    def update(self, entity: PortfolioCompanyShareOptionHolding) -> Optional[PortfolioCompanyShareOptionHolding]:
        pass

    def delete(self, id: int) -> bool:
        pass