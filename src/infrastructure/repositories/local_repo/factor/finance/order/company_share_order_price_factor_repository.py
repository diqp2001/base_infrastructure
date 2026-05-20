"""
Repository class for Company Share Order Price factor entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.company_share_order_price_factor_mapper import CompanyShareOrderPriceFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.ports.factor.company_share_order_price_factor_port import CompanyShareOrderPriceFactorPort


class CompanyShareOrderPriceFactorRepository(BaseFactorRepository, CompanyShareOrderPriceFactorPort):
    """Repository for Company Share Order Price factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanyShareOrderPriceFactorMapper()
        self.mapper_value = FactorValueMapper()
        
    @property
    def entity_class(self):
        return self.get_factor_entity()
        
    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """
        Get or create a company share order price factor (no dependencies - base factor).
        
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
                group=kwargs.get('group', 'order'),
                factor_type=kwargs.get('factor_type', 'company_share_order_price_factor')
            )
            if existing:
                return self._to_entity(existing)
            
            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'order'),
                subgroup=kwargs.get('subgroup', 'price'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'decimal'),
                source=kwargs.get('source', 'order_system'),
                definition=kwargs.get('definition', f'company_share order price factor: {primary_key}')
            )
            
            # Use FactorMapper to convert domain entity to ORM model
            # This ensures entity_type is properly set
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            
            # Order price is a base factor with no dependencies
            # No dependency creation needed
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create company share order price factor {primary_key}: {e}")
            return None

    def get_by_all(self, name: str, group: str, factor_type: Optional[str] = None, subgroup: Optional[str] = None, frequency: Optional[str] = None, data_type: Optional[str] = None, source: Optional[str] = None):
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
            print(f"Error retrieving company share order price factor by all attributes: {e}")
            return None

    def get_by_id(self, id: int):
        entity = self._to_entity(self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none())
        return entity
    
    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()
    
    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)