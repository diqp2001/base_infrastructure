from datetime import date
from typing import Optional

from src.domain.entities.finance.financial_assets.index.index_company_share import IndexCompanyShare
from src.infrastructure.models.finance.financial_assets.index import IndexModel


class IndexCompanyShareMapper:
    @property
    def discriminator(self):
        return 'IndexCompanyShare'

    @property
    def entity_class(self):
        return IndexCompanyShare

    @property
    def model_class(self):
        return IndexModel

    @staticmethod
    def to_domain(orm_obj: IndexModel) -> Optional[IndexCompanyShare]:
        if not orm_obj:
            return None
        return IndexCompanyShare(
            id=orm_obj.id,
            symbol=orm_obj.symbol,
            name=orm_obj.name,
            currency_id=orm_obj.currency_id,
        )

    @staticmethod
    def to_orm(domain_obj: IndexCompanyShare, orm_obj: Optional[IndexModel] = None) -> IndexModel:
        if orm_obj is None:
            orm_obj = IndexModel()
        orm_obj.symbol = domain_obj.symbol
        orm_obj.name = domain_obj.name
        orm_obj.currency_id = domain_obj.currency_id
        orm_obj.start_date = getattr(domain_obj, 'start_date', None) or date.today()
        orm_obj.end_date = getattr(domain_obj, 'end_date', None)
        return orm_obj
