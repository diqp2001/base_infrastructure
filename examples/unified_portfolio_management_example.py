"""
Unified Portfolio Management System Example

This example demonstrates how to use the new unified portfolio management system
in QCAlgorithm, which eliminates dual portfolio tracking by using domain entities
and repositories as the single source of truth.
"""

import logging
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the necessary classes
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.application.managers.project_managers.market_making_SPX_call_spread_project.backtesting.base_project_algorithm import Algorithm

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_session():
    """Create a test database session (in-memory SQLite for demo)."""
    try:
        # Create in-memory SQLite database for testing
        engine = create_engine('sqlite:///:memory:', echo=True)
        
        # Import and create all tables
        from src.infrastructure.models import Base
        Base.metadata.create_all(engine)
        
        # Create session factory
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("✅ Test database session created")
        return session
        
    except Exception as e:
        logger.error(f"❌ Failed to create test session: {e}")
        return None


def demonstrate_unified_portfolio_management():
    """Demonstrate the unified portfolio management system."""
    
    logger.info("🚀 Starting Unified Portfolio Management Demonstration")
    
    # 1. Setup database and repositories
    session = create_test_session()
    if not session:
        logger.error("Cannot proceed without database session")
        return
    
    # 2. Create repository factory
    repository_factory = RepositoryFactory(session)
    logger.info("✅ Repository factory created")
    
    # 3. Create algorithm with unified portfolio management
    algorithm = Algorithm(repository_factory=repository_factory)
    logger.info("✅ Algorithm created with repository factory")
    
    # 4. Initialize algorithm (this will register the portfolio)
    algorithm.initialize()
    logger.info("✅ Algorithm initialized")
    
    # 5. Check unified portfolio status
    if algorithm.is_unified_portfolio_enabled():
        logger.info("✅ Unified portfolio management is ENABLED")
        
        # Get initial portfolio state
        initial_state = algorithm.get_unified_portfolio_state()
        logger.info(f"📊 Initial Portfolio State: {initial_state}")
        
    else:
        logger.warning("⚠️ Unified portfolio management is NOT enabled")
        return
    
    # 6. Simulate trading operations
    logger.info("\n📈 Simulating Trading Operations...")
    
    # Mock market data
    mock_data = {
        'date': datetime.now(),
        'time': datetime.now().time(),
        'spx_price': 4500.0
    }
    
    # Execute a few mock trades to demonstrate order/transaction tracking
    try:
        # Trade 1: Long SPX position
        logger.info("🔄 Executing Trade 1: Long SPX position")
        
        # Create mock order ticket
        class MockOrderTicket:
            def __init__(self, symbol, quantity):
                self.order_id = f"ORDER_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                self.symbol = symbol
                self.quantity = quantity
                self.status = 'SUBMITTED'
                self.time = datetime.now()
        
        ticket1 = MockOrderTicket('SPX', 100)
        
        # Register the order using unified system
        order_entity = algorithm.register_order(ticket1)
        if order_entity:
            logger.info(f"✅ Order registered: {order_entity.id}")
        
        # Simulate order fill
        class MockOrderEvent:
            def __init__(self, order_id):
                self.order_id = order_id
                self.status = 'FILLED'
                self.time = datetime.now()
        
        fill_event = MockOrderEvent(ticket1.order_id)
        
        # Record transaction using unified system
        transaction = algorithm.record_transaction(fill_event)
        if transaction:
            logger.info(f"✅ Transaction recorded: {transaction.id}")
        
        # Trade 2: Short position
        logger.info("🔄 Executing Trade 2: Short position")
        ticket2 = MockOrderTicket('SPX', -50)
        order_entity2 = algorithm.register_order(ticket2)
        
        fill_event2 = MockOrderEvent(ticket2.order_id)
        transaction2 = algorithm.record_transaction(fill_event2)
        
        # Update portfolio values
        algorithm._update_portfolio_value(mock_data)
        
        # 7. Display unified portfolio status
        logger.info("\n📊 Final Portfolio Analysis...")
        
        # Get comprehensive state
        final_state = algorithm.get_algorithm_state()
        logger.info(f"🎯 Algorithm State: {final_state}")
        
        # Get orders summary
        orders_summary = algorithm.get_unified_orders_summary()
        logger.info(f"📋 Orders Summary: {orders_summary}")
        
        # Get transactions summary
        transactions_summary = algorithm.get_unified_transactions_summary()
        logger.info(f"💳 Transactions Summary: {transactions_summary}")
        
        # Get active positions
        positions = algorithm.get_unified_positions()
        logger.info(f"📈 Active Positions: {positions}")
        
        # Show portfolio value calculation
        portfolio_value = algorithm.get_unified_portfolio_value()
        logger.info(f"💰 Portfolio Value (Unified): ${portfolio_value:,.2f}")
        
        # 8. Compare with legacy system
        logger.info("\n🔍 Legacy vs Unified Comparison...")
        logger.info(f"Legacy Portfolio Value: ${algorithm.portfolio_value:,.2f}")
        logger.info(f"Unified Portfolio Value: ${portfolio_value:,.2f}")
        logger.info(f"QC Portfolio Cash: ${algorithm.portfolio.cash:,.2f}")
        
        if abs(algorithm.portfolio_value - portfolio_value) < 0.01:
            logger.info("✅ Portfolio values are synchronized")
        else:
            logger.warning("⚠️ Portfolio values are NOT synchronized")
            
    except Exception as e:
        logger.error(f"❌ Error during trading simulation: {e}")
    
    # 9. Cleanup
    session.close()
    logger.info("✅ Database session closed")
    logger.info("🎉 Unified Portfolio Management demonstration completed!")


def compare_legacy_vs_unified():
    """Compare legacy dual tracking vs unified portfolio management."""
    
    logger.info("\n🔍 Legacy vs Unified Portfolio Management Comparison")
    
    print("""
    ═══════════════════════════════════════════════════════════════════
    📊 LEGACY DUAL PORTFOLIO TRACKING (BEFORE)
    ═══════════════════════════════════════════════════════════════════
    
    ❌ Problems:
    • Two separate portfolio systems running in parallel
    • QCAlgorithm's SecurityPortfolioManager vs custom dict tracking  
    • Portfolio values calculated from custom positions, NOT QC system
    • Cash managed separately: self.cash ≠ self.portfolio.cash
    • Position data stored in parallel systems that may diverge
    • Repository integration was optional and disconnected
    
    📁 Data Storage:
    • self.positions = {} (custom dictionary)
    • self.cash = 0 (separate cash tracking)  
    • self.portfolio_value = self.cash + position_values (manual calc)
    • self.orders = {} (custom order tracking)
    
    ═══════════════════════════════════════════════════════════════════
    ✅ UNIFIED PORTFOLIO MANAGEMENT (AFTER)
    ═══════════════════════════════════════════════════════════════════
    
    ✅ Benefits:
    • Single source of truth using domain entities
    • Portfolio, Order, Holding, Position, Transaction entities
    • Repository-backed persistence for all operations
    • Automatic synchronization between QC and domain systems
    • Comprehensive tracking via PortfolioRepository, OrderRepository, etc.
    • Clean separation: trading logic vs portfolio management
    
    📁 Data Storage:
    • Portfolio entities stored in database via PortfolioRepository
    • Holding entities with Position relationships
    • Order entities with complete lifecycle tracking
    • Transaction entities for all executions
    • Automatic QC portfolio synchronization
    
    ═══════════════════════════════════════════════════════════════════
    🔧 IMPLEMENTATION CHANGES
    ═══════════════════════════════════════════════════════════════════
    
    QCAlgorithm Base Class:
    • Added UnifiedPortfolioManager integration
    • New methods: get_unified_portfolio_value(), get_unified_positions()
    • Automatic order/transaction registration
    • Portfolio value synchronization
    
    Algorithm (SPX Market Making):  
    • Updated _update_portfolio_value() to use unified system
    • Enhanced get_algorithm_state() with unified data
    • Legacy fallback for backward compatibility
    
    Repository Factory:
    • OrderRepository and TransactionRepository already available
    • PortfolioRepository and HoldingRepository integrated
    • Complete domain entity support
    
    ═══════════════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    # Show comparison first
    compare_legacy_vs_unified()
    
    # Then run the demonstration
    demonstrate_unified_portfolio_management()