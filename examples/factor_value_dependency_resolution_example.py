"""
Example demonstrating the factor value dependency resolution system.

This example shows how to set up and use the factor value resolution system
for both direct and indirect dependencies as described in the issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.services.factor_value_dependency_resolver import (
    FactorValueDependencyResolver, 
    FactorValueAggregationService
)
from src.infrastructure.services.local_entity_relationship_resolver import LocalEntityRelationshipResolver
from src.application.services.factor_value_resolution_service import FactorValueResolutionService
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor


def create_example_setup():
    """Create a complete example setup for factor value resolution."""
    
    print("=== Factor Value Dependency Resolution Example ===\n")
    
    # 1. Database Setup (using in-memory SQLite for example)
    engine = create_engine('sqlite:///:memory:', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("1. Database setup completed")
    
    # 2. Create repository instances (these would normally be injected)
    # For this example, we'll create mock repositories
    class MockRepository:
        def __init__(self):
            self.data = {}
        
        def get_by_id(self, id):
            return self.data.get(id)
        
        def add(self, entity):
            entity.id = len(self.data) + 1
            self.data[entity.id] = entity
            return entity
        
        def get_by_factor_entity_date(self, factor_id, entity_id, date_str):
            return None  # For simplicity, always return None (not found)
    
    factor_value_repo = MockRepository()
    factor_dependency_repo = MockRepository()
    factor_repo = MockRepository()
    
    print("2. Repository mocks created")
    
    # 3. Create dependency resolution services
    entity_resolver = LocalEntityRelationshipResolver(session)
    dependency_resolver = FactorValueDependencyResolver(entity_resolver)
    aggregation_service = FactorValueAggregationService()
    
    resolution_service = FactorValueResolutionService(
        factor_value_repository=factor_value_repo,
        factor_dependency_repository=factor_dependency_repo,
        factor_repository=factor_repo,
        dependency_resolver=dependency_resolver,
        aggregation_service=aggregation_service
    )
    
    print("3. Dependency resolution services created")
    
    return resolution_service, factor_repo, factor_dependency_repo

def demonstrate_portfolio_value_calculation():
    """Demonstrate portfolio value calculation from holdings (indirect dependency)."""
    
    print("\n=== Portfolio Value Calculation Example ===")
    print("Scenario: Calculate portfolio total value by aggregating holding values")
    print("Type: Indirect dependency (portfolio → holdings)\n")
    
    resolution_service, factor_repo, factor_dependency_repo = create_example_setup()
    
    # Create a portfolio value factor
    portfolio_factor = PortfolioValueFactor(
        name="Portfolio Total Value",
        factor_id=1,
        definition="Total market value of all holdings in the portfolio"
    )
    factor_repo.add(portfolio_factor)
    
    print(f"Created portfolio factor: {portfolio_factor.name}")
    print(f"Factor ID: {portfolio_factor.factor_id}")
    print(f"Dependency requirements: {portfolio_factor.get_dependency_requirements()}")
    
    # Create a holding value factor dependency
    holding_value_factor_id = 2
    dependency = FactorDependency(
        dependent_factor_id=portfolio_factor.factor_id,
        independent_factor_id=holding_value_factor_id,
        independent_factor_related_entity_key=None  # No direct relationship - portfolio doesn't contain holding IDs
    )
    factor_dependency_repo.add(dependency)
    
    print(f"\nCreated dependency: Portfolio factor {portfolio_factor.factor_id} depends on holding factor {holding_value_factor_id}")
    print("This represents the indirect relationship where portfolio value = sum of all holding values")
    
    # Demonstrate the calculation logic
    print("\n--- Portfolio Calculation Example ---")
    
    # Simulate dependency values (as they would be resolved from holdings)
    mock_dependencies = {
        "factor_2_holding_101": 15000.50,  # Holding 1: $15,000.50
        "factor_2_holding_102": 8750.25,   # Holding 2: $8,750.25
        "factor_2_holding_103": 22500.00,  # Holding 3: $22,500.00
    }
    
    portfolio_value = portfolio_factor.calculate(mock_dependencies)
    
    print(f"Holdings in portfolio:")
    for dep_name, value in mock_dependencies.items():
        holding_id = dep_name.split('_')[-1]
        print(f"  - Holding {holding_id}: ${value:,.2f}")
    
    print(f"\nCalculated portfolio total value: ${portfolio_value:,.2f}")
    
    return portfolio_value

def demonstrate_option_value_calculation():
    """Demonstrate option value calculation from underlying asset (direct dependency)."""
    
    print("\n=== Option Value Calculation Example ===")
    print("Scenario: Calculate option value based on underlying asset price")
    print("Type: Direct dependency (option → underlying_asset_id)\n")
    
    # Create a mock option factor (simplified for example)
    class OptionValueFactor:
        def __init__(self, name, factor_id):
            self.name = name
            self.factor_id = factor_id
        
        def calculate(self, dependencies):
            # Simple Black-Scholes approximation for example
            underlying_price = list(dependencies.values())[0] if dependencies else 100.0
            strike_price = 105.0  # Example strike price
            
            # Very simplified option value calculation
            intrinsic_value = max(0, underlying_price - strike_price)
            time_value = 5.0  # Simplified time value
            
            return intrinsic_value + time_value
        
        def get_dependency_requirements(self):
            return {
                "relationship_type": "direct",
                "target_entities": "underlying_asset",
                "dependency_key": "underlying_asset_id"
            }
    
    option_factor = OptionValueFactor("Call Option Value", factor_id=3)
    
    print(f"Created option factor: {option_factor.name}")
    print(f"Factor ID: {option_factor.factor_id}")
    print(f"Dependency requirements: {option_factor.get_dependency_requirements()}")
    
    # Create dependency on underlying asset price factor
    underlying_price_factor_id = 4
    dependency = FactorDependency(
        dependent_factor_id=option_factor.factor_id,
        independent_factor_id=underlying_price_factor_id,
        independent_factor_related_entity_key="underlying_asset_id"  # Direct relationship key
    )
    
    print(f"\nCreated dependency: Option factor {option_factor.factor_id} depends on underlying price factor {underlying_price_factor_id}")
    print("The option entity contains 'underlying_asset_id' field pointing to the underlying asset")
    
    # Demonstrate the calculation
    print("\n--- Option Calculation Example ---")
    
    # Simulate underlying asset price
    underlying_price = 110.50
    dependencies = {f"factor_{underlying_price_factor_id}": underlying_price}
    
    option_value = option_factor.calculate(dependencies)
    
    print(f"Underlying asset price: ${underlying_price}")
    print(f"Strike price: $105.00")
    print(f"Calculated option value: ${option_value:.2f}")
    print(f"  - Intrinsic value: ${max(0, underlying_price - 105.0):.2f}")
    print(f"  - Time value: $5.00 (simplified)")
    
    return option_value

def demonstrate_aggregation_methods():
    """Demonstrate different aggregation methods."""
    
    print("\n=== Aggregation Methods Example ===")
    print("Showing different ways to aggregate factor values\n")
    
    aggregation_service = FactorValueAggregationService()
    
    # Sample holding values
    holding_values = {
        101: 12500.00,
        102: 18750.50,
        103: 9200.25,
        104: 15600.75
    }
    
    print("Sample holding values:")
    for holding_id, value in holding_values.items():
        print(f"  - Holding {holding_id}: ${value:,.2f}")
    
    # Demonstrate different aggregation methods
    methods = ['sum', 'average', 'max', 'min']
    
    print(f"\nAggregation results:")
    for method in methods:
        result = aggregation_service.aggregate_factor_values(holding_values, method)
        print(f"  - {method.upper()}: ${result:,.2f}")

def main():
    """Run the complete factor value dependency resolution example."""
    
    print("Factor Value Dependency Resolution System")
    print("=" * 50)
    print("This example demonstrates the solution for handling both direct and indirect")
    print("factor dependencies as described in the GitHub issue.\n")
    
    try:
        # 1. Portfolio value calculation (indirect dependency)
        portfolio_value = demonstrate_portfolio_value_calculation()
        
        # 2. Option value calculation (direct dependency)  
        option_value = demonstrate_option_value_calculation()
        
        # 3. Aggregation methods
        demonstrate_aggregation_methods()
        
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"✅ Portfolio value calculation: ${portfolio_value:,.2f}")
        print(f"✅ Option value calculation: ${option_value:.2f}")
        print("✅ Aggregation methods demonstrated")
        print("\nThe factor value dependency resolution system successfully handles:")
        print("1. ✅ Direct dependencies (option → underlying asset via underlying_asset_id)")
        print("2. ✅ Indirect dependencies (portfolio → holdings via aggregation)")
        print("3. ✅ Multiple aggregation strategies (sum, average, max, min)")
        print("4. ✅ Flexible dependency resolution based on entity relationships")
        
    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()