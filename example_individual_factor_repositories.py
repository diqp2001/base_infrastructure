"""
Example demonstrating the use of individual factor repositories.
This replaces the previous factory pattern approach with separate repositories.
"""

from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Import specific factor repositories
from src.infrastructure.repositories.local_repo.factor import (
    # Geographic repositories
    ContinentFactorRepository,
    CountryFactorRepository,
    
    # Financial asset repositories
    IndexFactorRepository,
    ShareMomentumFactorRepository,
    ShareTechnicalFactorRepository,
    ShareTargetFactorRepository,
    ShareVolatilityFactorRepository,
    DerivativeFactorRepository
)

# Import the registry for easy access
from src.infrastructure.repositories.local_repo.factor.factor_repository_registry import FactorRepositoryRegistry

# Import factor entities
from src.domain.entities.factor.finance.financial_assets.index_factor import IndexFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor


def example_usage():
    """Example of using individual factor repositories."""
    
    # Create a mock session (replace with actual session in real code)
    engine = create_engine('sqlite:///:memory:')
    session = Session(engine)
    
    print("=== Individual Factor Repository Examples ===\n")
    
    # Example 1: Direct repository usage
    print("1. Direct Repository Usage:")
    index_repo = IndexFactorRepository(session)
    momentum_repo = ShareMomentumFactorRepository(session)
    
    print(f"   - Created IndexFactorRepository: {type(index_repo).__name__}")
    print(f"   - Created ShareMomentumFactorRepository: {type(momentum_repo).__name__}")
    
    # Example 2: Using the registry to get repositories dynamically
    print("\n2. Using FactorRepositoryRegistry:")
    
    # Get repository for IndexFactor
    index_repo_from_registry = FactorRepositoryRegistry.get_repository(IndexFactor, session)
    print(f"   - IndexFactor -> {type(index_repo_from_registry).__name__}")
    
    # Get repository for ShareMomentumFactor
    momentum_repo_from_registry = FactorRepositoryRegistry.get_repository(ShareMomentumFactor, session)
    print(f"   - ShareMomentumFactor -> {type(momentum_repo_from_registry).__name__}")
    
    # Example 3: Show all available mappings
    print("\n3. All Available Factor Repository Mappings:")
    mappings = FactorRepositoryRegistry.get_all_mappings()
    for factor_class, repo_class in mappings.items():
        print(f"   - {factor_class.__name__} -> {repo_class.__name__}")
    
    print(f"\n✅ Total factor repositories available: {len(mappings)}")
    
    # Example 4: Usage in entity service (simplified)
    print("\n4. Usage in Entity Service (Concept):")
    print("""
    # OLD PROBLEMATIC WAY:
    entity_factor_class_input = ENTITY_FACTOR_MAPPING[entity.__class__][0]
    factor = self.entity_service._create_or_get(
        entity_cls=Factor,
        entity_factor_class_input=entity_factor_class_input  # ❌ Confusing parameter
    )

    # NEW CLEAN WAY WITH INDIVIDUAL REPOSITORIES:
    factor_entity_class = ENTITY_FACTOR_MAPPING[entity.__class__][0]
    factor_repo = FactorRepositoryRegistry.get_repository(factor_entity_class, session)
    factor = factor_repo.get_or_create(
        primary_key=factor_name,
        group='price',
        subgroup='daily',
        data_type='numeric',
        source='market_data'
    )
    """)
    
    session.close()
    print("\n✅ Individual factor repositories working correctly!")


if __name__ == "__main__":
    example_usage()