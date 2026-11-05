"""
Mapper for ETFShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare as DomainETFShare
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel as ORMETFShare


class ETFShareMapper:
    """Mapper for ETFShare domain entity and ORM model."""
    @property
    def discriminator(self):
        return 'ETFShare'

    @property
    def entity_class(self):
        return DomainETFShare

    @property
    def model_class(self):
        return ORMETFShare

    @staticmethod
    def to_domain(orm_obj: ORMETFShare) -> DomainETFShare:
        """Convert ORM model to domain entity."""
        return DomainETFShare(
            id=orm_obj.id,
            symbol=orm_obj.symbol,
            currency_id=orm_obj.currency_id,
            exchange_id=orm_obj.exchange_id,
            name=orm_obj.name,
            issuer=orm_obj.issuer,
            asset_class=orm_obj.asset_class,
            leverage_factor=float(orm_obj.leverage_factor) if orm_obj.leverage_factor is not None else 1.0,
            replication=orm_obj.replication,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date,
        )

    @staticmethod
    def to_orm(domain_obj: DomainETFShare, orm_obj: Optional[ORMETFShare] = None) -> ORMETFShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMETFShare()
        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.exchange_id = domain_obj.exchange_id
        orm_obj.currency_id = domain_obj.currency_id
        orm_obj.issuer = domain_obj.issuer
        orm_obj.asset_class = domain_obj.asset_class
        orm_obj.leverage_factor = domain_obj.leverage_factor
        orm_obj.replication = domain_obj.replication
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        return orm_obj
