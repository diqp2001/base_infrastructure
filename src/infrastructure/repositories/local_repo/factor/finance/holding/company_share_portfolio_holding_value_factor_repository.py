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

    

    def _create_or_get (self, entity_symbol, **kwargs) -> CompanySharePortfolioHoldingValueFactor:
        """
        Enhanced create or get method with automatic dependency creation for holding value factors.
        
        Holding value depends on position values (quantity × price calculations).
        """
        try:
            # 1. Create the main holding value factor
            name = kwargs.get("name")
            group = kwargs.get("group")
            subgroup = kwargs.get("subgroup")
            data_type = kwargs.get("data_type")
            source = kwargs.get("source")
            definition = kwargs.get("definition")
            entity_type = kwargs.get("entity_type")
            frequency = kwargs.get("frequency", "1d")
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
            
            # 3. Create dependency factors and relationships
            for dependency in dependencies.items():
                entity_class = dependency[1].get('class')
                repo = self.factory.get_local_repository(entity_class)
                
                dependency_config = dependency[1]
                dependency_entity = repo._create_or_get(
                    entity_class,
                    primary_key=dependency_config.get("name"),
                    group=dependency_config.get("group"),
                    subgroup=dependency_config.get("subgroup"),
                    frequency=dependency_config.get("frequency", "1d"),
                    data_type=dependency_config.get("data_type"),
                    source=dependency_config.get("source"),
                    definition=dependency_config.get("definition"),
                )

                # 4. Create factor dependency relationship
                repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                lag = dependency_config.get("parameters", {}).get("lag", None) if dependency_config.get("parameters") else None
                independent_factor_related_entity_key = dependency_config.get("parameters", {}).get("independent_factor_related_entity_key", None) if dependency_config.get("parameters") else None
                
                repo_factor_dependency._create_or_get(
                    independent_factor=dependency_entity, 
                    dependent_factor=self._to_entity(orm_factor), 
                    lag=lag, 
                    independent_factor_related_entity_key=independent_factor_related_entity_key,
                    dependency_name=dependency[0]
                )
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            self.session.rollback()
            print(f"Error creating holding value factor with dependencies: {e}")
            return None