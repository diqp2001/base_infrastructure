"""
Mapper for CashFlowStatement domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from decimal import Decimal

from src.domain.entities.finance.financial_statements.cash_flow_statement import CashFlowStatement as DomainCashFlowStatement
from src.infrastructure.models.finance.financial_statements.cash_flow_statement import CashFlowStatementModel as ORMCashFlowStatement


class CashFlowStatementMapper:
    """Mapper for CashFlowStatement domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCashFlowStatement) -> DomainCashFlowStatement:
        """Convert ORM model to domain entity."""
        domain_entity = DomainCashFlowStatement(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            period=orm_obj.period,
            year=orm_obj.year,
            operating_cash_flow=Decimal(str(orm_obj.operating_cash_flow)) if hasattr(orm_obj, 'operating_cash_flow') and orm_obj.operating_cash_flow else Decimal('0'),
            investing_cash_flow=Decimal(str(orm_obj.investing_cash_flow)) if hasattr(orm_obj, 'investing_cash_flow') and orm_obj.investing_cash_flow else Decimal('0'),
            financing_cash_flow=Decimal(str(orm_obj.financing_cash_flow)) if hasattr(orm_obj, 'financing_cash_flow') and orm_obj.financing_cash_flow else Decimal('0')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCashFlowStatement, orm_obj: Optional[ORMCashFlowStatement] = None) -> ORMCashFlowStatement:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCashFlowStatement(
                company_id=domain_obj.company_id,
                period=domain_obj.period,
                year=domain_obj.year,
                operating_cash_flow=float(domain_obj.operating_cash_flow) if hasattr(domain_obj, 'operating_cash_flow') and domain_obj.operating_cash_flow else 0.0,
                investing_cash_flow=float(domain_obj.investing_cash_flow) if hasattr(domain_obj, 'investing_cash_flow') and domain_obj.investing_cash_flow else 0.0,
                financing_cash_flow=float(domain_obj.financing_cash_flow) if hasattr(domain_obj, 'financing_cash_flow') and domain_obj.financing_cash_flow else 0.0
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.period = domain_obj.period
        orm_obj.year = domain_obj.year
        
        # Map cash flow data
        if hasattr(domain_obj, 'operating_cash_flow'):
            orm_obj.operating_cash_flow = float(domain_obj.operating_cash_flow) if domain_obj.operating_cash_flow else 0.0
        if hasattr(domain_obj, 'investing_cash_flow'):
            orm_obj.investing_cash_flow = float(domain_obj.investing_cash_flow) if domain_obj.investing_cash_flow else 0.0
        if hasattr(domain_obj, 'financing_cash_flow'):
            orm_obj.financing_cash_flow = float(domain_obj.financing_cash_flow) if domain_obj.financing_cash_flow else 0.0
        
        # Set statement type
        orm_obj.statement_type = 'cash_flow_statement'
        
        return orm_obj