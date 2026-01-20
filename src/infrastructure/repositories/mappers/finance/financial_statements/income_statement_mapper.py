"""
Mapper for IncomeStatement domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from decimal import Decimal

from src.domain.entities.finance.financial_statements.income_statement import IncomeStatement as DomainIncomeStatement
from src.infrastructure.models.finance.financial_statements.income_statement import IncomeStatementModel as ORMIncomeStatement


class IncomeStatementMapper:
    """Mapper for IncomeStatement domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMIncomeStatement) -> DomainIncomeStatement:
        """Convert ORM model to domain entity."""
        domain_entity = DomainIncomeStatement(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            period=orm_obj.period,
            year=orm_obj.year,
            revenue=Decimal(str(orm_obj.revenue)) if hasattr(orm_obj, 'revenue') and orm_obj.revenue else Decimal('0'),
            expenses=Decimal(str(orm_obj.expenses)) if hasattr(orm_obj, 'expenses') and orm_obj.expenses else Decimal('0'),
            net_income=Decimal(str(orm_obj.net_income)) if hasattr(orm_obj, 'net_income') and orm_obj.net_income else Decimal('0')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainIncomeStatement, orm_obj: Optional[ORMIncomeStatement] = None) -> ORMIncomeStatement:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMIncomeStatement(
                company_id=domain_obj.company_id,
                period=domain_obj.period,
                year=domain_obj.year,
                revenue=float(domain_obj.revenue) if hasattr(domain_obj, 'revenue') and domain_obj.revenue else 0.0,
                expenses=float(domain_obj.expenses) if hasattr(domain_obj, 'expenses') and domain_obj.expenses else 0.0,
                net_income=float(domain_obj.net_income) if hasattr(domain_obj, 'net_income') and domain_obj.net_income else 0.0
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.period = domain_obj.period
        orm_obj.year = domain_obj.year
        
        # Map financial data
        if hasattr(domain_obj, 'revenue'):
            orm_obj.revenue = float(domain_obj.revenue) if domain_obj.revenue else 0.0
        if hasattr(domain_obj, 'expenses'):
            orm_obj.expenses = float(domain_obj.expenses) if domain_obj.expenses else 0.0
        if hasattr(domain_obj, 'net_income'):
            orm_obj.net_income = float(domain_obj.net_income) if domain_obj.net_income else 0.0
        
        # Set statement type
        orm_obj.statement_type = 'income_statement'
        
        return orm_obj