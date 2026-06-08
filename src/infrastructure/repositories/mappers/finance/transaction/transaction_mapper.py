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
        """Convert ORM model to domain entity.

        TransactionModel only persists the columns below; domain-only fields
        (portfolio_id, holding_id, account_id, currency_id, exchange_id) are
        not stored in the DB and default to None on load.
        """
        return DomainTransaction(
            id=orm_obj.id,
            portfolio_id=getattr(orm_obj, 'portfolio_id', None),
            holding_id=getattr(orm_obj, 'holding_id', None),
            order_id=orm_obj.order_id,
            date=orm_obj.date,
            transaction_type=orm_obj.transaction_type,
            transaction_id=orm_obj.transaction_id,
            account_id=getattr(orm_obj, 'account_id', None),
            trade_date=orm_obj.trade_date,
            value_date=orm_obj.value_date,
            settlement_date=orm_obj.settlement_date,
            status=orm_obj.status,
            spread=orm_obj.spread,
            currency_id=getattr(orm_obj, 'currency_id', None),
            exchange_id=getattr(orm_obj, 'exchange_id', None),
            external_transaction_id=orm_obj.external_transaction_id,
        )

    @staticmethod
    def to_orm(domain_obj: DomainTransaction, orm_obj: Optional[ORMTransaction] = None) -> ORMTransaction:
        """Convert domain entity to ORM model.

        Only the columns that exist on TransactionModel are written;
        domain-only fields (portfolio_id, holding_id, account_id,
        currency_id, exchange_id) are intentionally omitted.
        """
        # Normalise enum fields to string names so SQLEnum .upper() works
        def _to_str(val):
            return val.name if hasattr(val, 'name') else val

        if orm_obj is None:
            orm_obj = ORMTransaction(
                order_id=domain_obj.order_id,
                date=domain_obj.date,
                transaction_type=_to_str(domain_obj.transaction_type),
                transaction_id=domain_obj.transaction_id,
                trade_date=domain_obj.trade_date,
                value_date=domain_obj.value_date,
                settlement_date=domain_obj.settlement_date,
                status=_to_str(domain_obj.status),
                spread=domain_obj.spread,
                external_transaction_id=domain_obj.external_transaction_id,
            )

        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id
        orm_obj.order_id = domain_obj.order_id
        orm_obj.date = domain_obj.date
        orm_obj.transaction_type = _to_str(domain_obj.transaction_type)
        orm_obj.transaction_id = domain_obj.transaction_id
        orm_obj.trade_date = domain_obj.trade_date
        orm_obj.value_date = domain_obj.value_date
        orm_obj.settlement_date = domain_obj.settlement_date
        orm_obj.status = _to_str(domain_obj.status)
        orm_obj.spread = domain_obj.spread
        orm_obj.external_transaction_id = domain_obj.external_transaction_id

        return orm_obj