from typing import List, Optional
from src.domain.entities.finance.portfolio.derivative_portfolio import DerivativePortfolio


class DerivativePortfolioPort:

    def get_by_id(self, id: int) -> Optional[DerivativePortfolio]:
        pass

    def get_by_name(self, name: str) -> Optional[DerivativePortfolio]:
        pass

    def get_all(self) -> List[DerivativePortfolio]:
        pass

    def add(self, entity: DerivativePortfolio) -> Optional[DerivativePortfolio]:
        pass

    def update(self, entity: DerivativePortfolio) -> Optional[DerivativePortfolio]:
        pass

    def delete(self, id: int) -> bool:
        pass