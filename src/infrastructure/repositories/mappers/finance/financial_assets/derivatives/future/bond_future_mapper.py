from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
from src.infrastructure.models.finance.financial_assets.derivative.future.future import FutureModel


class BondFutureMapper:
    """Mapper between BondFuture domain entity and FutureModel ORM row."""

    @property
    def discriminator(self):
        return 'BondFuture'

    @property
    def entity_class(self):
        return BondFuture

    @property
    def model_class(self):
        return FutureModel

    @staticmethod
    def to_domain(orm_obj: FutureModel) -> Optional[BondFuture]:
        if not orm_obj:
            return None
        return BondFuture(
            id=orm_obj.id,
            name=orm_obj.name if hasattr(orm_obj, 'name') else None,
            symbol=orm_obj.symbol,
            currency_id=orm_obj.currency_id if hasattr(orm_obj, 'currency_id') else None,
            exchange_id=orm_obj.exchange_id if hasattr(orm_obj, 'exchange_id') else None,
            underlying_asset_id=orm_obj.underlying_asset_id if hasattr(orm_obj, 'underlying_asset_id') else None,
            start_date=orm_obj.start_date if hasattr(orm_obj, 'start_date') else None,
            end_date=orm_obj.end_date if hasattr(orm_obj, 'end_date') else None,
            contract_size=orm_obj.contract_size if hasattr(orm_obj, 'contract_size') else None,
        )

    @staticmethod
    def to_orm(domain_obj: BondFuture) -> FutureModel:
        orm_obj = FutureModel()
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.currency_id = getattr(domain_obj, 'currency_id', None)
        orm_obj.exchange_id = getattr(domain_obj, 'exchange_id', None)
        orm_obj.underlying_asset_id = getattr(domain_obj, 'underlying_asset_id', None)
        orm_obj.start_date = getattr(domain_obj, 'start_date', None)
        orm_obj.end_date = getattr(domain_obj, 'end_date', None)
        orm_obj.contract_size = getattr(domain_obj, 'contract_size', None)
        return orm_obj
