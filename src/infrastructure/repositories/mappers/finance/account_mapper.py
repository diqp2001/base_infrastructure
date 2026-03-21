"""
Mapper for Account domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.account import Account as DomainAccount
from src.infrastructure.models.finance.account import AccountModel as ORMAccount


class AccountMapper:
    """Mapper for Account domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMAccount) -> DomainAccount:
        """Convert ORM model to domain entity."""
        domain_entity = DomainAccount(
            id=orm_obj.id,
            account_id=orm_obj.account_id,
            account_type=orm_obj.account_type,
            status=orm_obj.status,
            base_currency_id=orm_obj.base_currency_id,
            created_at=orm_obj.created_at
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainAccount, orm_obj: Optional[ORMAccount] = None) -> ORMAccount:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMAccount(
                account_id=domain_obj.account_id,
                account_type=domain_obj.account_type,
                status=domain_obj.status,
                base_currency_id=domain_obj.base_currency_id,
                created_at=domain_obj.created_at
            )
        
        # Map basic fields
        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id
        orm_obj.account_id = domain_obj.account_id
        orm_obj.account_type = domain_obj.account_type
        orm_obj.status = domain_obj.status
        orm_obj.base_currency_id = domain_obj.base_currency_id
        orm_obj.created_at = domain_obj.created_at
        
        return orm_obj