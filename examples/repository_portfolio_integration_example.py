"""
Example: PortfolioRepository Integration with QCAlgorithm

This example demonstrates how to use the enhanced QCAlgorithm with RepositoryFactory
for persistent portfolio, order, transaction, and holding tracking in the 
market making SPX call spread project.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.application.managers.project_managers.market_making_SPX_call_spread_project.backtesting.base_project_algorithm import Algorithm


def create_enhanced_spx_algorithm_example():
    """
    Example showing how to create SPX algorithm with repository integration.
    """
    
    # 1. Setup database session (in practice, this would use your existing database)
    engine = create_engine('sqlite:///example_trading.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 2. Create RepositoryFactory with all required repositories
    repository_factory = RepositoryFactory(session)
    
    print("✅ Created RepositoryFactory with repositories:")
    print(f"  - Portfolio: {repository_factory.portfolio_local_repo is not None}")
    print(f"  - Order: {repository_factory.order_local_repo is not None}")
    print(f"  - Transaction: {repository_factory.transaction_local_repo is not None}")
    print(f"  - Holding: {repository_factory.holding_local_repo is not None}")
    
    # 3. Create SPX Algorithm with repository integration
    algorithm = Algorithm(repository_factory=repository_factory)
    
    # 4. Alternatively, inject the factory after creation
    # algorithm = Algorithm()
    # algorithm.set_factory(repository_factory)
    
    print("✅ Created SPX Algorithm with repository integration")
    
    # 5. Initialize algorithm (this will register the portfolio)
    try:
        algorithm.initialize()
        print("✅ Algorithm initialized successfully")
        
        if algorithm._current_portfolio_entity:
            print(f"📊 Portfolio registered: {algorithm._current_portfolio_entity.name}")
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
    
    return algorithm, session


def demonstrate_order_tracking():
    """
    Example showing how order and transaction tracking works.
    """
    print("\n" + "="*50)
    print("DEMO: Order and Transaction Tracking")
    print("="*50)
    
    algorithm, session = create_enhanced_spx_algorithm_example()
    
    try:
        # Create mock market data
        mock_data = {
            'date': '2024-01-15',
            'spx_price': 4500,
            'time': '14:30:00'
        }
        
        # Demonstrate order placement with repository tracking
        print("\n📋 Placing market orders...")
        
        # These orders will automatically be registered in the repository
        long_order = algorithm.market_order('SPX', 10, tag="DEMO_LONG")
        short_order = algorithm.market_order('SPX', -5, tag="DEMO_SHORT")
        
        print(f"✅ Long order: {long_order.order_id}")
        print(f"✅ Short order: {short_order.order_id}")
        
        # Check if orders were tracked in repository
        if algorithm.repository_factory and algorithm._current_portfolio_entity:
            order_repo = algorithm.repository_factory.order_local_repo
            portfolio_orders = order_repo.get_by_portfolio_id(
                algorithm._current_portfolio_entity.id
            )
            print(f"📊 Orders in repository: {len(portfolio_orders)}")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        
    finally:
        session.close()


def demonstrate_backtest_runner_integration():
    """
    Example showing how to integrate with BacktestRunner.
    """
    print("\n" + "="*50) 
    print("DEMO: BacktestRunner Integration")
    print("="*50)
    
    class MockBacktestRunner:
        def __init__(self, session):
            self.session = session
            self.repository_factory = RepositoryFactory(session)
            
        def create_algorithm(self) -> Algorithm:
            """Create algorithm instance with repository factory."""
            # Create algorithm with factory injection
            algorithm = Algorithm(repository_factory=self.repository_factory)
            
            # You can inject other dependencies here
            # algorithm.set_strategy(strategy)
            # algorithm.set_factor_manager(factor_manager)  
            # algorithm.set_trainer(trainer)
            
            return algorithm
            
        def run_backtest(self, start_date, end_date):
            """Run backtest with repository-backed algorithm."""
            try:
                # Create algorithm with factory
                algorithm = self.create_algorithm()
                
                # Initialize and validate
                algorithm.initialize()
                
                # Verify portfolio was registered
                if algorithm._current_portfolio_entity:
                    print(f"✅ Algorithm portfolio: {algorithm._current_portfolio_entity.name}")
                    print(f"📊 Portfolio ID: {algorithm._current_portfolio_entity.id}")
                else:
                    print("⚠️ No portfolio entity registered")
                
                # Run backtest logic here...
                print("✅ Backtest simulation completed")
                
                return {'success': True, 'portfolio_id': algorithm._current_portfolio_entity.id}
                
            except Exception as e:
                print(f"❌ Backtest error: {e}")
                return {'success': False, 'error': str(e)}
    
    # Demo usage
    engine = create_engine('sqlite:///backtest_example.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        runner = MockBacktestRunner(session)
        results = runner.run_backtest('2024-01-01', '2024-01-31')
        print(f"📈 Backtest results: {results}")
        
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 PortfolioRepository Integration Examples")
    print("=" * 50)
    
    # Run examples
    demonstrate_order_tracking()
    demonstrate_backtest_runner_integration()
    
    print("\n✅ All examples completed!")
    print("\nKey Benefits:")
    print("- ✅ Clean separation: QCAlgorithm focuses on trading logic")
    print("- ✅ Repository pattern: All persistence handled via repositories") 
    print("- ✅ Factory injection: Single point of dependency management")
    print("- ✅ SPX Ready: Specifically designed for call spread trading")
    print("- ✅ DDD Compliant: Follows your established architecture patterns")
    print("- ✅ Optional: Algorithm works with or without repository integration")