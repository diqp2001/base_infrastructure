"""
Mapper for Transaction domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.transaction.transaction import Transaction as DomainTransaction
from src.infrastructure.models.finance.transaction.transaction import TransactionModel as ORMTransaction


class TransactionMapper:
    """Mapper for Transaction domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMTransaction) -> DomainTransaction:
        """Convert ORM model to domain entity."""
        domain_entity = DomainTransaction(
            id=orm_obj.id,
            portfolio_id=orm_obj.portfolio_id,
            holding_id=orm_obj.holding_id,
            order_id=orm_obj.order_id,
            date=orm_obj.date,
            transaction_type=orm_obj.transaction_type,
            transaction_id=orm_obj.transaction_id,
            account_id=orm_obj.account_id,
            trade_date=orm_obj.trade_date,
            value_date=orm_obj.value_date,
            settlement_date=orm_obj.settlement_date,
            status=orm_obj.status,
            spread=orm_obj.spread,
            currency_id=orm_obj.currency_id,
            exchange_id=orm_obj.exchange_id,
            external_transaction_id=orm_obj.external_transaction_id
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainTransaction, orm_obj: Optional[ORMTransaction] = None) -> ORMTransaction:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMTransaction(
                portfolio_id=domain_obj.portfolio_id,
                holding_id=domain_obj.holding_id,
                order_id=domain_obj.order_id,
                date=domain_obj.date,
                transaction_type=domain_obj.transaction_type,
                transaction_id=domain_obj.transaction_id,
                account_id=domain_obj.account_id,
                trade_date=domain_obj.trade_date,
                value_date=domain_obj.value_date,
                settlement_date=domain_obj.settlement_date,
                status=domain_obj.status,
                spread=domain_obj.spread,
                currency_id=domain_obj.currency_id,
                exchange_id=domain_obj.exchange_id,
                external_transaction_id=domain_obj.external_transaction_id
            )
        
        # Map basic fields
        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id
        orm_obj.portfolio_id = domain_obj.portfolio_id
        orm_obj.holding_id = domain_obj.holding_id
        orm_obj.order_id = domain_obj.order_id
        orm_obj.date = domain_obj.date
        orm_obj.transaction_type = domain_obj.transaction_type
        orm_obj.transaction_id = domain_obj.transaction_id
        orm_obj.account_id = domain_obj.account_id
        orm_obj.trade_date = domain_obj.trade_date
        orm_obj.value_date = domain_obj.value_date
        orm_obj.settlement_date = domain_obj.settlement_date
        orm_obj.status = domain_obj.status
        orm_obj.spread = domain_obj.spread
        orm_obj.currency_id = domain_obj.currency_id
        orm_obj.exchange_id = domain_obj.exchange_id
        orm_obj.external_transaction_id = domain_obj.external_transaction_id
        
        return orm_obj