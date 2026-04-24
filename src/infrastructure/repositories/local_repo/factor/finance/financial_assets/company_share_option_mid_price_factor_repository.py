"""
src/infrastructure/repositories/local_repo/factor/finance/financial_assets/company_share_option_mid_price_factor_repository.py

Local repository for CompanyShareOptionMidPriceFactor operations.
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.ports.factor.company_share_option_mid_price_factor_port import CompanyShareOptionMidPriceFactorPort
from src.infrastructure.repositories.mappers.factor.company_share_option_mid_price_factor_mapper import CompanyShareOptionMidPriceFactorMapper


class CompanyShareOptionMidPriceFactorRepository(CompanyShareOptionMidPriceFactorPort):
    """Local repository for CompanyShareOptionMidPriceFactor operations."""

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CompanyShareOptionMidPriceFactorMapper()

    @property
    def entity_class(self):
        return self.mapper.get_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self,entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Create new factor or get existing one."""
        try:

            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'company_share_option'),
                subgroup=kwargs.get('subgroup', 'price'),
                frequency=kwargs.get('frequency'),
                factor_type=kwargs.get('factor_type', 'company_share_option_mid_price_factor'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market')
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'company_share_option'),
                subgroup=kwargs.get('subgroup', 'price'),
                frequency=kwargs.get('frequency'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
            )
            # Use FactorMapper to convert domain entity to ORM model
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)

            #create_or_get dependencies
            if kwargs.get('dependencies'):
                dependencies = kwargs.get('dependencies')
                for dependency in dependencies.items():
                    entity_class = dependency[1].get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    
                    dependency_config = dependency[1]
                    dependency_entity = repo._create_or_get(
                            entity_class,
                            primary_key=dependency_config.get("name"),
                            group=dependency_config.get("group"),
                            subgroup=dependency_config.get("subgroup"),
                            frequency=dependency_config.get("frequency"),
                            data_type=dependency_config.get("data_type"),
                            source=dependency_config.get("source"),
                            definition=dependency_config.get("definition"),)


                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    lag = dependency_config.get("parameters", {}).get("lag",None) if dependency_config.get("parameters") else None
                    independent_factor_related_entity_key = dependency_config.get("parameters", {}).get("independent_factor_related_entity_key",None) if dependency_config.get("parameters") else None
                    repo_factor_dependency._create_or_get(independent_factor=dependency_entity, dependent_factor=self._to_entity(orm_factor), lag = lag, independent_factor_related_entity_key=independent_factor_related_entity_key )
 
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            

        except Exception as e:
            print(f"Error creating/getting CompanyShareOptionMidPriceFactor {primary_key}: {e}")
            self.session.rollback()
            return None
        

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain(infra_obj)
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by name."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.name == name)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_by_id(self, id: int) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by ID."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()
        return self.mapper.to_domain(obj)

    def get_all(self) -> List[CompanyShareOptionMidPriceFactor]:
        """Get all factors."""
        objs = self.session.query(self.model_class).all()
        return [self.mapper.to_domain(o) for o in objs]

    def add(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Add new factor."""
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Update existing factor."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == entity.id)\
            .one_or_none()

        if not obj:
            return None

        obj.name = entity.name
        obj.group = entity.group
        obj.subgroup = entity.subgroup
        obj.frequency = entity.frequency
        obj.data_type = entity.data_type
        obj.source = entity.source
        obj.definition = entity.definition

        self.session.commit()
        return self.mapper.to_domain(obj)

    def delete(self, id: int) -> bool:
        """Delete factor by ID."""
        obj = self.session.query(self.model_class)\
            .filter(self.model_class.id == id)\
            .one_or_none()

        if not obj:
            return False

        self.session.delete(obj)
        self.session.commit()
        return True