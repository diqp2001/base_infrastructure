"""
Repository class for Index Future Option Price Return factor entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.infrastructure.repositories.mappers.factor.index_future_option_price_return_factor_mapper import IndexFutureOptionPriceReturnFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository


class IndexFutureOptionPriceReturnFactorRepository(BaseFactorRepository):
    """Repository for Index Future Option Price Return factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = IndexFutureOptionPriceReturnFactorMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def get_by_id(self, id: int):
        return (
            self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )
    
    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return IndexFutureOptionPriceReturnFactorMapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return IndexFutureOptionPriceReturnFactorMapper.to_orm(entity)

    def _create_or_get(self, primary_key: str, **kwargs):
        """
        Get or create an index future option price return factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'index_future_option'),
                subgroup=kwargs.get('subgroup', 'return'),
                factor_type=kwargs.get('factor_type', 'return'),
                data_type=self.mapper.discriminator,
                source=kwargs.get('source', 'market_data')
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'index_future_option'),
                subgroup=kwargs.get('subgroup', 'return'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
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
                            primary_key=dependency_config.get("name"),
                            group=dependency_config.get("group"),
                            subgroup=dependency_config.get("subgroup"),
                            data_type=dependency_config.get("data_type"),
                            factor_type=dependency_config.get("factor_type"),
                            source=dependency_config.get("source"),
                            definition=dependency_config.get("definition"),)


                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    lag = dependency_config.get("parameters", {}).get("lag") if dependency_config.get("parameters") else None
                    repo_factor_dependency._create_or_get(independent_factor = dependency_entity,dependent_factor = self._to_entity(orm_factor), lag=lag)
 
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create for index future option price return factor {primary_key}: {e}")
            return None
        
    def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: Optional[str] = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Retrieve a factor matching all provided (non-None) fields."""
        try:
            FactorModel = self.get_factor_model()

            query = self.session.query(FactorModel)

            # Mandatory filters
            query = query.filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )

            # Optional filters
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
            print(f"Error retrieving factor by all attributes: {e}")
            return None