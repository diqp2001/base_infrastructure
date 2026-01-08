from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_statements.financial_statement import FinancialStatement


class FinancialStatementPort(ABC):
    """Port interface for FinancialStatement entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_company_id(self, company_id: int) -> List[FinancialStatement]:
        """Retrieve financial statements by company ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[FinancialStatement]:
        """Retrieve all financial statements."""
        pass
    
    @abstractmethod
    def get_by_period(self, period: str) -> List[FinancialStatement]:
        """Retrieve financial statements by reporting period."""
        pass
    
    @abstractmethod
    def get_by_year(self, year: int) -> List[FinancialStatement]:
        """Retrieve financial statements by year."""
        pass
    
    @abstractmethod
    def get_by_company_and_period(self, company_id: int, period: str, year: int) -> Optional[FinancialStatement]:
        """Retrieve a specific financial statement by company, period, and year."""
        pass
    
    @abstractmethod
    def add(self, statement: FinancialStatement) -> FinancialStatement:
        """Add a new financial statement."""
        pass
    
    @abstractmethod
    def update(self, statement: FinancialStatement) -> FinancialStatement:
        """Update an existing financial statement."""
        pass
    
    @abstractmethod
    def delete(self, company_id: int, period: str, year: int) -> bool:
        """Delete a financial statement by company, period, and year."""
        pass