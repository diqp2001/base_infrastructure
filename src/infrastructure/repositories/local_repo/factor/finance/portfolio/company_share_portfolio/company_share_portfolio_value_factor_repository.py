"""
Repository class for Portfolio Company Share Value factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.domain.entities.factor.factor_dependency import FactorDependency


class CompanySharePortfolioValueFactorRepository(BaseFactorRepository):
    """Repository for Portfolio Company Share Value factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = FactorMapper() # Consider using a specific mapper for portfolio company share value factors if needed

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain_portfolio_company_share_value_factor(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)

    

    def _create_or_get (self, entity_symbol, **kwargs) -> CompanySharePortfolioValueFactor:
        """
        Enhanced create or get method with automatic dependency creation for portfolio value factors.
        
        Portfolio value depends on the sum of all holding values within the portfolio.
        """
        try:
            name = kwargs.get("name")
            group = kwargs.get("group")
            subgroup = kwargs.get("subgroup")
            data_type = kwargs.get("data_type")
            source = kwargs.get("source")
            definition = kwargs.get("definition")
            entity_type = kwargs.get("entity_type")
            frequency = kwargs.get("frequency", "1d")
            # 1. Create the main portfolio value factor
            orm_factor = self.session.query(self.get_factor_model()).filter(
                self.get_factor_model().name == name
            ).first()
            
            if orm_factor:
                return self._to_entity(orm_factor)
            
            # Create new portfolio value factor
            portfolio_factor = CompanySharePortfolioValueFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type=data_type,
                source=source,
                definition=definition
            )
            
            # Convert to ORM and save
            orm_factor = self._to_model(portfolio_factor)
            self.session.add(orm_factor)
            self.session.flush()  # Get ID without committing
            
            # 2. Define portfolio value dependencies configuration
            dependencies = {
                "holding_values": {
                    "class": CompanySharePortfolioHoldingValueFactor,
                    "name": "Portfolio Company Share Holding Value",
                    "group": "holding",
                    "subgroup": "value",
                    "frequency": frequency,
                    "data_type": "decimal",
                    "source": "portfolio_holding_analysis",
                    "definition": "Total value of company share holding (quantity × price)",
                    "parameters": {
                        "lag": None,
                        "independent_factor_related_entity_key": "holding_id"
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
            print(f"Error creating portfolio value factor with dependencies: {e}")
            return None