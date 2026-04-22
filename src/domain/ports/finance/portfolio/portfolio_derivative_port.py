from typing import List, Optional
from src.domain.entities.finance.portfolio.portfolio_derivative import PortfolioDerivative


class PortfolioDerivativePort:

    def get_by_id(self, id: int) -> Optional[PortfolioDerivative]:
        pass

    def get_by_name(self, name: str) -> Optional[PortfolioDerivative]:
        pass

    def get_all(self) -> List[PortfolioDerivative]:
        pass

    def add(self, entity: PortfolioDerivative) -> Optional[PortfolioDerivative]:
        pass

    def update(self, entity: PortfolioDerivative) -> Optional[PortfolioDerivative]:
        pass

    def delete(self, id: int) -> bool:
        pass