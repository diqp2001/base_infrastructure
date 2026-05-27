from typing import Optional
from src.domain.entities.entity import Entity


class FinancialStatement(Entity):
    """
    Base class for financial statements.
    """

    def __init__(self, id: Optional[int] = None, company_id: int = None,
                 period: str = None, year: int = None):
        super().__init__(id)
        self.company_id = company_id
        self.period = period
        self.year = year
