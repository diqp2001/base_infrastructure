"""
Mapper for FinancialStatement domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_statements.financial_statement import FinancialStatement as DomainFinancialStatement
from src.infrastructure.models.finance.financial_statements.financial_statement import FinancialStatementModel as ORMFinancialStatement


class FinancialStatementMapper:
    """Mapper for FinancialStatement domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMFinancialStatement) -> DomainFinancialStatement:
        """Convert ORM model to domain entity."""
        domain_entity = DomainFinancialStatement(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            period=orm_obj.period,
            year=orm_obj.year,
            statement_type=getattr(orm_obj, 'statement_type', 'financial_statement')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainFinancialStatement, orm_obj: Optional[ORMFinancialStatement] = None) -> ORMFinancialStatement:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMFinancialStatement(
                company_id=domain_obj.company_id,
                period=domain_obj.period,
                year=domain_obj.year
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.period = domain_obj.period
        orm_obj.year = domain_obj.year
        
        # Map statement type if available
        if hasattr(domain_obj, 'statement_type'):
            orm_obj.statement_type = domain_obj.statement_type
        elif not hasattr(orm_obj, 'statement_type') or orm_obj.statement_type is None:
            orm_obj.statement_type = 'financial_statement'
        
        return orm_obj