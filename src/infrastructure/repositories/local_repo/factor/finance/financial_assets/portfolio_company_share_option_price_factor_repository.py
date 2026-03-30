"""
Repository class for Portfolio Company Share Option Price factor entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.portfolio_company_share_option_price_factor_mapper import PortfolioCompanyShareOptionPriceFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository


class PortfolioCompanyShareOptionPriceFactorRepository(BaseFactorRepository):
    """Repository for Portfolio Company Share Option Price factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = PortfolioCompanyShareOptionPriceFactorMapper()

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
        return PortfolioCompanyShareOptionPriceFactorMapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return PortfolioCompanyShareOptionPriceFactorMapper.to_orm(entity)

    def _create_or_get(self, entity_cls,primary_key: str, **kwargs):
        """
        Get or create a portfolio company share option price factor with dependency resolution.
        
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
                group=kwargs.get('group', 'portfolio_company_share_option'),
                subgroup=kwargs.get('subgroup', 'price'),
                factor_type=kwargs.get('factor_type', 'pricing'),
                data_type=self.mapper.discriminator,
                source=kwargs.get('source', 'market_data')
            )
            if existing:
                return self._to_entity(existing)

            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'portfolio_company_share_option'),
                subgroup=kwargs.get('subgroup', 'price'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
            )
            
            # Use FactorMapper to convert domain entity to ORM model
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share option price factor {primary_key}: {e}")
            return None
        
    def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: str = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Retrieve a factor matching all non-id fields."""
        try:
            FactorModel = self.get_factor_model()

            query = self.session.query(FactorModel).filter(
                FactorModel.name == name,
                FactorModel.group == group,
                FactorModel.factor_type == factor_type,
                FactorModel.subgroup == subgroup,
                FactorModel.frequency == frequency,
                FactorModel.data_type == data_type,
                FactorModel.source == source,
            )

            factor = query.first()
            return factor

        except Exception as e:
            print(f"Error retrieving portfolio company share option price factor by all attributes: {e}")
            return None