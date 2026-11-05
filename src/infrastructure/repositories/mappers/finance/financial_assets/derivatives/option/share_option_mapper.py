"""
Mapper for ShareOption domain entities (CompanyShareOption, ETFShareOption) and their ORM models.
Subclasses name the domain class, the ORM class and the discriminator; the field mapping is written once.
"""

from typing import Optional
from datetime import datetime


class ShareOptionMapper:
    """Field mapping shared by every option on a share."""
    domain_class = None
    orm_class = None
    DISCRIMINATOR = None

    @property
    def discriminator(self):
        return self.DISCRIMINATOR

    @property
    def entity_class(self):
        return self.domain_class

    @property
    def model_class(self):
        return self.orm_class

    @classmethod
    def to_domain(cls, orm_obj):
        """Convert ORM model to domain entity."""
        return cls.domain_class(
            id=orm_obj.id,
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            currency_id=getattr(orm_obj, 'currency_id', None),
            underlying_asset_id=getattr(orm_obj, 'underlying_asset_id', None),
            exchange_id=getattr(orm_obj, 'exchange_id', None),
            option_type=getattr(orm_obj, 'option_type', None),
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None),
            strike_price=getattr(orm_obj, 'strike_price', None),
            multiplier=getattr(orm_obj, 'multiplier', None),
            expiry=getattr(orm_obj, 'expiry', None)
        )

    @classmethod
    def to_orm(cls, domain_obj, orm_obj: Optional[object] = None):
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = cls.orm_class()

        # Map basic fields
        orm_obj.id = domain_obj.id

        # Map share option specific fields
        for field in ('option_type', 'currency_id', 'underlying_asset_id', 'exchange_id', 'strike_price',
                      'multiplier', 'expiry', 'name', 'symbol', 'start_date', 'end_date'):
            if hasattr(domain_obj, field):
                setattr(orm_obj, field, getattr(domain_obj, field))

        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()

        return orm_obj
