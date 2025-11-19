# PortfolioService

## Overview

The `PortfolioService` provides comprehensive portfolio management capabilities for financial applications, enabling creation, tracking, and analysis of investment portfolios and positions. It serves as the central hub for portfolio lifecycle management, position tracking, P&L calculations, and performance analytics.

## Responsibilities

### Portfolio Management
- **Portfolio Creation**: Create and configure new investment portfolios with initial capital
- **Portfolio Tracking**: Monitor portfolio composition, cash balances, and overall value
- **Portfolio Analytics**: Calculate performance metrics, returns, and risk indicators
- **Portfolio Reporting**: Generate comprehensive portfolio reports with detailed analytics

### Position Management
- **Position Entry**: Add new positions to portfolios with entry price and quantity tracking
- **Position Monitoring**: Track current market values, unrealized P&L, and position status
- **Position Exit**: Close positions with realized P&L calculation and cash flow updates
- **Position Analytics**: Analyze individual position performance and contribution to portfolio

### Performance Calculation
- **Valuation Metrics**: Calculate total portfolio value, market value, and cash balances
- **P&L Analysis**: Track realized and unrealized gains/losses across all positions
- **Return Calculation**: Compute absolute and percentage returns for portfolios
- **Performance Reporting**: Generate detailed performance reports with win/loss analytics

## Architecture

### Service Design
```python
class PortfolioService:
    def __init__(self, db_type: str = 'sqlite'):
        self.database_service = DatabaseService(db_type)
```

### Database Integration
- **DatabaseService Integration**: Leverages centralized database service for persistence
- **Transaction Management**: Ensures data consistency across portfolio and position operations
- **SQL-Based Operations**: Uses direct SQL queries for optimal performance with financial data
- **Error Handling**: Comprehensive exception handling with automatic rollbacks

## Key Features

### 1. Portfolio Lifecycle Management
```python
# Create portfolio
service = PortfolioService()
portfolio = service.create_portfolio(
    name="Tech Growth Portfolio",
    description="Focus on technology growth stocks",
    initial_cash=Decimal('100000.00'),
    currency='USD',
    benchmark='QQQ'
)

# Add positions
position = service.add_position(
    portfolio_id=portfolio['id'],
    symbol='AAPL',
    quantity=100,
    entry_price=Decimal('150.00'),
    position_type='long'
)
```

### 2. Position Tracking and Updates
```python
# Update position with current market price
service.update_position_price(position_id=1, current_price=Decimal('155.00'))

# Close position
service.close_position(
    position_id=1,
    exit_price=Decimal('160.00'),
    exit_date=date.today()
)
```

### 3. Portfolio Analytics
```python
# Calculate portfolio value and metrics
valuation = service.calculate_portfolio_value(portfolio_id=1)
print(f"Total Portfolio Value: ${valuation['total_portfolio_value']:,.2f}")
print(f"Total Return: {valuation['total_return_pct']:.2f}%")

# Generate comprehensive report
report = service.generate_portfolio_report(portfolio_id=1)
print(f"Win Rate: {report['performance_metrics']['win_rate']:.1f}%")
```

### 4. Historical Analysis
```python
# Get portfolio history
history = service.get_portfolio_history(
    portfolio_id=1,
    start_date=date(2023, 1, 1),
    end_date=date.today()
)
```

## Usage Patterns

### Investment Tracking Application
```python
class InvestmentTracker:
    def __init__(self):
        self.portfolio_service = PortfolioService('postgresql')
    
    def create_user_portfolio(self, user_id: int, portfolio_name: str, initial_investment: Decimal):
        # Create portfolio for user
        portfolio = self.portfolio_service.create_portfolio(
            name=f"{user_id}_{portfolio_name}",
            initial_cash=initial_investment,
            description=f"Portfolio for user {user_id}"
        )
        
        return portfolio
    
    def buy_stock(self, portfolio_id: int, symbol: str, shares: int, price: Decimal):
        # Add new position
        position = self.portfolio_service.add_position(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=shares,
            entry_price=price,
            position_type='long'
        )
        
        return position
    
    def sell_stock(self, position_id: int, price: Decimal):
        # Close position
        return self.portfolio_service.close_position(position_id, price)
```

### Trading Algorithm Performance Tracking
```python
class TradingAlgorithmTracker:
    def __init__(self, algorithm_name: str):
        self.portfolio_service = PortfolioService()
        self.algorithm_name = algorithm_name
        
        # Create dedicated portfolio for algorithm
        self.portfolio = self.portfolio_service.create_portfolio(
            name=f"Algorithm_{algorithm_name}",
            initial_cash=Decimal('1000000.00'),
            description=f"Portfolio tracking {algorithm_name} algorithm performance"
        )
    
    def record_trade(self, symbol: str, action: str, quantity: int, price: Decimal):
        if action == 'BUY':
            return self.portfolio_service.add_position(
                portfolio_id=self.portfolio['id'],
                symbol=symbol,
                quantity=quantity,
                entry_price=price
            )
        elif action == 'SELL':
            # Find open position for symbol
            positions = self.portfolio_service.get_portfolio_positions(
                self.portfolio['id'], status='open'
            )
            
            for pos in positions:
                if pos['symbol'] == symbol and pos['quantity'] >= quantity:
                    return self.portfolio_service.close_position(pos['id'], price)
    
    def get_algorithm_performance(self):
        return self.portfolio_service.generate_portfolio_report(self.portfolio['id'])
```

### Portfolio Rebalancing Service
```python
class PortfolioRebalancer:
    def __init__(self):
        self.portfolio_service = PortfolioService()
    
    def rebalance_portfolio(self, portfolio_id: int, target_allocations: Dict[str, float]):
        """Rebalance portfolio to target allocations."""
        # Get current positions
        positions = self.portfolio_service.get_portfolio_positions(portfolio_id, 'open')
        portfolio_value = self.portfolio_service.calculate_portfolio_value(portfolio_id)
        
        current_allocations = {}
        for pos in positions:
            symbol = pos['symbol']
            weight = pos['market_value'] / portfolio_value['total_portfolio_value']
            current_allocations[symbol] = weight
        
        # Calculate rebalancing trades
        trades = []
        for symbol, target_weight in target_allocations.items():
            current_weight = current_allocations.get(symbol, 0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.01:  # 1% threshold
                trades.append({
                    'symbol': symbol,
                    'action': 'BUY' if weight_diff > 0 else 'SELL',
                    'target_value': target_weight * portfolio_value['total_portfolio_value']
                })
        
        return trades
```

## Data Models

### Portfolio Structure
```python
portfolio = {
    'id': int,
    'name': str,
    'description': str,
    'initial_cash': float,
    'current_cash': float,
    'currency': str,
    'benchmark': str,
    'created_at': datetime,
    'status': str  # 'active', 'inactive', 'closed'
}
```

### Position Structure
```python
position = {
    'id': int,
    'portfolio_id': int,
    'symbol': str,
    'quantity': int,
    'entry_price': float,
    'current_price': float,
    'entry_date': date,
    'exit_date': date,
    'exit_price': float,
    'position_type': str,  # 'long', 'short'
    'market_value': float,
    'unrealized_pnl': float,
    'realized_pnl': float,
    'status': str  # 'open', 'closed'
}
```

## Performance Metrics

### Portfolio Valuation
- **Total Portfolio Value**: Sum of all position market values plus cash
- **Market Value**: Current value of all open positions
- **Cash Balance**: Available cash for new investments
- **Initial Value**: Starting portfolio value for return calculations

### Return Calculations
- **Total Return**: Absolute dollar gain/loss from initial investment
- **Total Return %**: Percentage return on initial investment
- **Realized P&L**: Profits/losses from closed positions
- **Unrealized P&L**: Current gains/losses on open positions

### Trading Analytics
- **Win Rate**: Percentage of profitable trades
- **Average Win**: Average profit per winning trade
- **Average Loss**: Average loss per losing trade
- **Profit Factor**: Ratio of average win to average loss

## Database Operations

### Transaction Management
```python
# All operations use proper transaction management
try:
    # Multiple database operations
    self.database_service.session.execute(query1, params1)
    self.database_service.session.execute(query2, params2)
    self.database_service.session.commit()
except Exception:
    self.database_service.session.rollback()
```

### Query Optimization
- **Parameterized Queries**: All queries use parameter binding for security and performance
- **Index Usage**: Designed to leverage database indexes on portfolio_id and symbol columns
- **Batch Operations**: Efficient handling of multiple position updates
- **Result Caching**: Position data cached during calculations to minimize database calls

## Error Handling and Validation

### Comprehensive Error Management
- **Database Errors**: Automatic rollback on transaction failures
- **Validation Errors**: Input validation for all numeric and date fields
- **Business Logic Errors**: Validation of sufficient cash for purchases, position existence for updates
- **Data Integrity**: Maintains referential integrity between portfolios and positions

### Logging and Monitoring
- **Operation Logging**: Success/failure logging for all major operations
- **Performance Tracking**: Monitor calculation performance for large portfolios
- **Error Reporting**: Detailed error messages with context information
- **Audit Trail**: Track all portfolio modifications for compliance

## Configuration and Customization

### Database Configuration
```python
# Supports multiple database backends
service = PortfolioService('postgresql')  # Production
service = PortfolioService('sqlite')      # Development/Testing
```

### Currency Support
- **Multi-currency Portfolios**: Support for different base currencies
- **Currency Conversion**: Framework for currency conversion (requires external rate provider)
- **Localization**: Support for different decimal precision based on currency

## Dependencies

### Required Packages
```python
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime
import pandas as pd
from src.application.services.database_service import DatabaseService
```

### External Dependencies
- **DatabaseService**: Centralized database operations and session management
- **pandas**: Data analysis and historical data processing
- **decimal**: Precise decimal arithmetic for financial calculations

## Testing Strategy

### Unit Testing
```python
def test_portfolio_creation():
    service = PortfolioService('sqlite')
    portfolio = service.create_portfolio(
        name="Test Portfolio",
        initial_cash=Decimal('10000.00')
    )
    assert portfolio['name'] == "Test Portfolio"
    assert portfolio['initial_cash'] == 10000.0
```

### Integration Testing
```python
def test_position_lifecycle():
    service = PortfolioService('sqlite')
    
    # Create portfolio
    portfolio = service.create_portfolio("Test", initial_cash=Decimal('10000'))
    
    # Add position
    position = service.add_position(
        portfolio['id'], 'AAPL', 100, Decimal('150.00')
    )
    
    # Update price
    success = service.update_position_price(position['id'], Decimal('155.00'))
    assert success
    
    # Close position
    success = service.close_position(position['id'], Decimal('160.00'))
    assert success
```

### Performance Testing
- **Large Portfolio Testing**: Test with portfolios containing hundreds of positions
- **Calculation Performance**: Benchmark portfolio valuation with large datasets
- **Database Performance**: Test query performance under load
- **Concurrent Access**: Test multiple users accessing portfolios simultaneously

## Best Practices

### Financial Data Handling
1. **Use Decimal for precision** - Always use Decimal for monetary amounts
2. **Validate input data** - Check for negative quantities, invalid dates, etc.
3. **Maintain data consistency** - Use transactions for multi-step operations
4. **Audit trail maintenance** - Log all portfolio modifications
5. **Currency consistency** - Ensure all calculations use consistent currency

### Performance Optimization
1. **Minimize database queries** - Batch operations where possible
2. **Cache calculation results** - Store intermediate results for complex calculations
3. **Use appropriate indexes** - Ensure database tables are properly indexed
4. **Optimize report generation** - Use efficient queries for portfolio reports
5. **Memory management** - Handle large portfolios efficiently

### Security and Compliance
1. **Data validation** - Validate all inputs before database operations
2. **Access control** - Implement proper user access controls (outside service scope)
3. **Audit logging** - Maintain detailed logs of all portfolio modifications
4. **Data encryption** - Use encrypted database connections for sensitive data
5. **Compliance reporting** - Support regulatory reporting requirements