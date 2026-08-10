from typing import Optional
from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_value_factor_mapper import CompanySharePortfolioOptionValueFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.domain.ports.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_value_factor_port import CompanySharePortfolioOptionValueFactorPort
from ......base_factor_repository import BaseFactorRepository


class CompanySharePortfolioOptionValueFactorRepository(BaseFactorRepository, CompanySharePortfolioOptionValueFactorPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanySharePortfolioOptionValueFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def get_factor_model(self):
        return self.mapper.get_factor_model()

    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()

    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        return self.mapper.to_domain(infra_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)

    def get_by_id(self, id: int):
        return self._to_entity(
            self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        )

    def get_by_name(self, name: str):
        return self._to_entity(
            self.session.query(self.model_class).filter(self.model_class.name == name).first()
        )

    def get_all(self):
        return [self._to_entity(m) for m in self.session.query(self.model_class).all()]

    def add(self, entity):
        orm = self._to_model(entity)
        self.session.add(orm)
        self.session.commit()
        return self._to_entity(orm)

    def update(self, entity):
        orm = self.session.query(self.model_class).filter(self.model_class.id == entity.id).one_or_none()
        if not orm:
            return None
        for k, v in vars(entity).items():
            if hasattr(orm, k) and k != 'id':
                setattr(orm, k, v)
        self.session.commit()
        return self._to_entity(orm)

    def delete(self, id: int) -> bool:
        orm = self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        if not orm:
            return False
        self.session.delete(orm)
        self.session.commit()
        return True

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        try:
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group') or 'value',
                factor_type=kwargs.get('factor_type') or 'company_share_portfolio_option_value_factor',
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group') or 'value',
                subgroup=kwargs.get('subgroup') or 'asset',
                frequency=kwargs.get('frequency') or '1d',
                data_type=kwargs.get('data_type') or 'decimal',
                source=kwargs.get('source') or 'calculated',
                definition=kwargs.get('definition') or f'CompanySharePortfolioOptionValueFactor: {primary_key}',
            )
            orm_factor = self._to_model(domain_factor)
            self.session.add(orm_factor)
            self.session.commit()
            return self._to_entity(orm_factor)
        except Exception as e:
            print(f"Error in _create_or_get CompanySharePortfolioOptionValueFactor {primary_key}: {e}")
            return None

    def get_by_all(self, name: str, group: str, factor_type: str = None,
                   subgroup: Optional[str] = None, frequency: Optional[str] = None,
                   data_type: Optional[str] = None, source: Optional[str] = None):
        try:
            FactorModel = self.get_factor_model()
            query = self.session.query(FactorModel).filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )
            if factor_type is not None:
                query = query.filter(FactorModel.factor_type == factor_type)
            if subgroup is not None:
                query = query.filter(FactorModel.subgroup == subgroup)
            if frequency is not None:
                query = query.filter(FactorModel.frequency == frequency)
            if data_type is not None:
                query = query.filter(FactorModel.data_type == data_type)
            if source is not None:
                query = query.filter(FactorModel.source == source)
            return query.first()
        except Exception as e:
            print(f"Error retrieving CompanySharePortfolioOptionValueFactor by all attributes: {e}")
            return None
