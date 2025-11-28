"""
Mapper for Bond domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from src.domain.entities.finance.financial_assets.bond import Bond as DomainBond
from src.infrastructure.models.finance.financial_assets.bond import Bond as ORMBond


class BondMapper:
    """Mapper for Bond domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMBond) -> DomainBond:
        """Convert ORM model to domain entity."""
        if not orm_obj:
            return None
            
        # Create domain entity
        domain_entity = DomainBond(
            cusip=orm_obj.cusip or orm_obj.isin,  # Use CUSIP or ISIN as identifier
            issuer=orm_obj.issuer,
            maturity_date=orm_obj.maturity_date,
            coupon_rate=Decimal(str(orm_obj.coupon_rate)),
            par_value=Decimal(str(orm_obj.face_value)) if orm_obj.face_value else Decimal('1000'),
            bond_type=orm_obj.bond_type,
            payment_frequency=orm_obj.payment_frequency or 2
        )
        
        # Set additional properties if available
        if orm_obj.current_price:
            domain_entity._price = Decimal(str(orm_obj.current_price))
            
        if orm_obj.yield_to_maturity:
            domain_entity._yield_to_maturity = Decimal(str(orm_obj.yield_to_maturity))
            
        if orm_obj.duration:
            domain_entity._duration = Decimal(str(orm_obj.duration))
            
        if orm_obj.credit_rating:
            domain_entity.update_credit_rating(orm_obj.credit_rating)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainBond, orm_obj: Optional[ORMBond] = None) -> ORMBond:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMBond()
        
        # Map basic fields
        orm_obj.isin = domain_obj.cusip  # Use CUSIP as ISIN for now
        orm_obj.cusip = domain_obj.cusip
        orm_obj.name = f"{domain_obj.issuer} Bond"
        orm_obj.issuer = domain_obj.issuer
        orm_obj.bond_type = domain_obj.bond_type
        orm_obj.currency = 'USD'  # Default currency
        
        # Bond terms
        orm_obj.face_value = domain_obj.par_value
        orm_obj.coupon_rate = domain_obj.coupon_rate
        orm_obj.issue_date = date.today()  # Default to today if not available
        orm_obj.maturity_date = domain_obj.maturity_date
        orm_obj.payment_frequency = domain_obj.payment_frequency
        
        # Credit information
        if hasattr(domain_obj, 'credit_rating') and domain_obj.credit_rating:
            orm_obj.credit_rating = domain_obj.credit_rating
        
        # Market data
        if hasattr(domain_obj, '_price') and domain_obj._price:
            orm_obj.current_price = domain_obj._price
            
        if hasattr(domain_obj, '_yield_to_maturity') and domain_obj._yield_to_maturity:
            orm_obj.yield_to_maturity = domain_obj._yield_to_maturity
            
        if hasattr(domain_obj, '_duration') and domain_obj._duration:
            orm_obj.duration = domain_obj._duration
            
        orm_obj.last_update = datetime.now()
        orm_obj.is_tradeable = True
        orm_obj.is_callable = False
        
        return orm_obj

    @staticmethod
    def to_infrastructure(domain_obj: DomainBond) -> ORMBond:
        """Legacy method name for backward compatibility."""
        return BondMapper.to_orm(domain_obj)