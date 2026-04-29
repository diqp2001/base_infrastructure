from typing import List, Optional
from domain.entities.finance.portfolio.company_share_option_portfolio import CompanyShareOptionPortfolio


class CompanyShareOptionPortPortfolio:

    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolio]:
        pass

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolio]:
        pass

    def get_all(self) -> List[CompanyShareOptionPortfolio]:
        pass

    def add(self, entity: CompanyShareOptionPortfolio) -> Optional[CompanyShareOptionPortfolio]:
        pass

    def update(self, entity: CompanyShareOptionPortfolio) -> Optional[CompanyShareOptionPortfolio]:
        pass

    def delete(self, id: int) -> bool:
        pass