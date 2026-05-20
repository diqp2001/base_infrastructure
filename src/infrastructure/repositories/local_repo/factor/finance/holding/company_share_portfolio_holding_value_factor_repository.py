"""
Repository class for Portfolio Company Share Holding Value factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.finance.holding.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.domain.entities.factor.factor_dependency import FactorDependency


class CompanySharePortfolioHoldingValueFactorRepository(BaseFactorRepository):
    """Repository for Portfolio Company Share Holding Value factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = FactorMapper()

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return CompanySharePortfolioHoldingValueFactor

    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return FactorMapper.to_domain_portfolio_company_share_holding_value_factor(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return FactorMapper.to_orm(entity)

    def get_or_create(self,entity_cls, primary_key: str, **kwargs):
        """
        Get or create a portfolio company share holding value factor with dependency resolution.
        
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
            
            # Create new factor using enhanced _create_or_get method with dependencies
            return self._create_or_get_with_dependencies(
                name=primary_key,
                group=kwargs.get('group', 'holding'),
                subgroup=kwargs.get('subgroup', 'value'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'portfolio_holding_analysis'),
                definition=kwargs.get('definition', f'Portfolio company share holding value factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'portfolio_company_share_holding_value'),
                frequency=kwargs.get('frequency', '1d')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share holding value factor {primary_key}: {e}")
            return None

    def _create_or_get_with_dependencies(self, name: str, group: str, subgroup: str, 
                                       data_type: str, source: str, definition: str, 
                                       entity_type: str, frequency: str = '1d') -> CompanySharePortfolioHoldingValueFactor:
        """
        Enhanced create or get method with automatic dependency creation for holding value factors.
        
        Holding value depends on position values (quantity × price calculations).
        """
        try:
            # 1. Create the main holding value factor
            orm_factor = self.session.query(self.get_factor_model()).filter(
                self.get_factor_model().name == name
            ).first()
            
            if orm_factor:
                return self._to_entity(orm_factor)
            
            # Create new holding value factor
            holding_factor = CompanySharePortfolioHoldingValueFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type=data_type,
                source=source,
                definition=definition
            )
            
            # Convert to ORM and save
            orm_factor = self._to_model(holding_factor)
            self.session.add(orm_factor)
            self.session.flush()  # Get ID without committing
            
            # 2. Define holding value dependencies configuration
            # For now, we'll create placeholder position value dependencies
            # These would be implemented when position value factors are created
            dependencies = {
                "position_values": {
                    "name": "Company Share Position Value",
                    "group": "position", 
                    "subgroup": "value",
                    "frequency": frequency,
                    "data_type": "decimal",
                    "source": "position_analysis",
                    "definition": "Total value of company share position (quantity × price)",
                    "parameters": {
                        "lag": None,
                        "independent_factor_related_entity_key": "position_id"
                    }
                }
            }
            
            # Note: Dependencies would be created here when position factor classes exist
            # For now, we're documenting the structure
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            self.session.rollback()
            print(f"Error creating holding value factor with dependencies: {e}")
            return None