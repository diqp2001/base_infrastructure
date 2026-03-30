"""
Repository class for Company Share Option Rho factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import CompanyShareOptionRhoFactor


class CompanyShareOptionRhoFactorRepository(BaseFactorRepository):
    """Repository for Company Share Option Rho factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = FactorMapper()

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return CompanyShareOptionRhoFactor

    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return FactorMapper.to_domain_company_share_option_rho_factor(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return FactorMapper.to_orm(entity)

    def get_or_create(self, entity_cls,primary_key: str, **kwargs):
        """
        Get or create a company share option rho factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_name(primary_key)
            if existing:
                return existing
            
            # Create new factor using base _create_or_get method
            return self._create_or_get(
                name=primary_key,
                group=kwargs.get('group', 'derivative'),
                subgroup=kwargs.get('subgroup', 'option_rho'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'options_analysis'),
                definition=kwargs.get('definition', f'Company share option rho factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'company_share_option_rho')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for company share option rho factor {primary_key}: {e}")
            return None