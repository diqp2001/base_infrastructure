"""
Mapper for BalanceSheet domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from decimal import Decimal

from src.domain.entities.finance.financial_statements.balance_sheet import BalanceSheet as DomainBalanceSheet
from src.infrastructure.models.finance.financial_statements.balance_sheet import BalanceSheetModel as ORMBalanceSheet


class BalanceSheetMapper:
    """Mapper for BalanceSheet domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMBalanceSheet) -> DomainBalanceSheet:
        """Convert ORM model to domain entity."""
        domain_entity = DomainBalanceSheet(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            period=orm_obj.period,
            year=orm_obj.year,
            assets=Decimal(str(orm_obj.assets)) if orm_obj.assets else Decimal('0'),
            liabilities=Decimal(str(orm_obj.liabilities)) if orm_obj.liabilities else Decimal('0'),
            equity=Decimal(str(orm_obj.equity)) if orm_obj.equity else Decimal('0')
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainBalanceSheet, orm_obj: Optional[ORMBalanceSheet] = None) -> ORMBalanceSheet:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMBalanceSheet(
                company_id=domain_obj.company_id,
                period=domain_obj.period,
                year=domain_obj.year,
                assets=float(domain_obj.assets) if domain_obj.assets else 0.0,
                liabilities=float(domain_obj.liabilities) if domain_obj.liabilities else 0.0,
                equity=float(domain_obj.equity) if domain_obj.equity else 0.0
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.period = domain_obj.period
        orm_obj.year = domain_obj.year
        orm_obj.assets = float(domain_obj.assets) if domain_obj.assets else 0.0
        orm_obj.liabilities = float(domain_obj.liabilities) if domain_obj.liabilities else 0.0
        orm_obj.equity = float(domain_obj.equity) if domain_obj.equity else 0.0
        
        # Set statement type
        orm_obj.statement_type = 'balance_sheet'
        
        return orm_obj