"""
Mapper for FinancialAsset domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""
from typing import Optional

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset as DomainFinancialAsset
from src.domain.entities.finance.financial_assets.index.index import Index as IndexEntity
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.currency import Currency as CurrencyEntity

from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel as ORMFinancialAsset


class FinancialAssetMapper:
    """Mapper for FinancialAsset domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_obj: Optional[ORMFinancialAsset]) -> Optional[DomainFinancialAsset]:
        """Convert ORM model to domain entity based on asset_type discriminator."""
        if not orm_obj:
            return None

        asset_type = orm_obj.asset_type

        base_args = {
            "id": orm_obj.id,
            "name": orm_obj.name,
            "symbol": orm_obj.symbol,
            "start_date": orm_obj.start_date,
            "end_date": orm_obj.end_date,
        }

        if asset_type == "index":
            return IndexEntity(
                **base_args,
            )

        elif asset_type == "company_share":
            return CompanyShare(
                **base_args,
                company_id=orm_obj.company_id,
                currency_id=orm_obj.currency_id,
            )

        elif asset_type == "currency":
            return CurrencyEntity(
                **base_args,
            )

        else:
            # Fallback: base FinancialAsset
            return DomainFinancialAsset(**base_args)

    @staticmethod
    def to_orm(domain_obj: DomainFinancialAsset, orm_obj: Optional[ORMFinancialAsset] = None) -> ORMFinancialAsset:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMFinancialAsset(
                asset_type=domain_obj.asset_type,  # Use the domain entity's asset_type
                name=domain_obj.name,
                symbol=domain_obj.symbol,
                description=getattr(domain_obj, 'description', None)
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'description'):
            orm_obj.description = domain_obj.description
        if hasattr(domain_obj, 'asset_type'):
            orm_obj.asset_type = domain_obj.asset_type
            
        return orm_obj