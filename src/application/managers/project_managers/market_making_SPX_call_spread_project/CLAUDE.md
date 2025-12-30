# CLAUDE.md – SPX Call Spread Market Making Project

## 🎯 Purpose

The **SPX Call Spread Market Making Project** is a sophisticated trading system designed specifically for systematic market making in S&P 500 (SPX) call spreads. This project implements advanced options pricing models, risk management systems, and automated trading strategies to provide liquidity in SPX call spread markets while managing risk and generating consistent returns.

## 🧬 Project Architecture

This project follows the established architectural patterns from the `test_base_project` while specializing in SPX options market making:

### Core Components

```
src/application/managers/project_managers/market_making_SPX_call_spread_project/
├── CLAUDE.md                           # This documentation file
├── __init__.py                         # Package initialization
├── project_manager.py                  # Main manager class
├── config.py                           # Configuration settings
├── 
├── data/                               # Data management components
│   ├── __init__.py
│   ├── data_loader.py                  # SPX data loading and IBKR integration
│   └── factor_manager.py               # SPX-specific factor management
│
├── models/                             # Pricing and modeling components
│   ├── __init__.py
│   ├── pricing_engine.py               # Black-Scholes and Greeks calculations
│   └── volatility_model.py             # IV surface and volatility forecasting
│
├── strategy/                           # Trading strategy components
│   ├── __init__.py
│   ├── market_making_strategy.py       # Core market making logic
│   └── risk_manager.py                 # Comprehensive risk management
│
├── backtesting/                        # Backtesting framework
│   ├── __init__.py
│   ├── backtest_runner.py              # Backtesting engine
│   └── base_project_algorithm.py       # Trading algorithm implementation
│
└── utils/                              # Utility components
    ├── __init__.py
    ├── performance_metrics.py          # Performance analysis tools
    └── validators.py                   # Data validation utilities
```

## 🔄 Pipeline Flow

### Stage 1: **Data Verification & Import**
1. **SPX Data Check**
   - Query database for existing SPX index data
   - Check data completeness and quality
   - Identify missing date ranges

2. **Data Import (if needed)**
   - Use IBKR API (`get_index_historical_data`) to fetch SPX data
   - Import using `MarketData.get_index_historical_data(symbol="SPX")`
   - Store in factor system for consistent access

3. **Factor Creation**
   - Generate SPX price factors (OHLCV)
   - Calculate technical indicators (SMA, RSI, MACD, Bollinger Bands)
   - Create volatility factors (realized volatility, ATR, Garman-Klass)

### Stage 2: **Market Making Strategy Setup**
4. **Strategy Initialization**
   - Initialize `CallSpreadMarketMakingStrategy`
   - Configure risk management with `RiskManager`
   - Setup pricing engine and volatility models

5. **Market Analysis**
   - Analyze current market regime (VIX levels, trend analysis)
   - Configure strategy parameters based on market conditions
   - Set up opportunity scanning parameters

### Stage 3: **Options Pricing & Selection**
6. **Volatility Surface Construction**
   - Build implied volatility surface from option market data
   - Calculate term structure and volatility skew
   - Implement volatility forecasting models

7. **Spread Opportunity Generation**
   - Generate bull and bear call spread opportunities
   - Apply delta targeting and width constraints
   - Score opportunities based on risk-adjusted returns

### Stage 4: **Risk Management & Execution**
8. **Position Risk Assessment**
   - Check portfolio exposure limits (delta, gamma, vega, theta)
   - Validate concentration limits across expiries and strikes
   - Run stress test scenarios

9. **Trade Execution Simulation**
   - Execute trades in backtest environment
   - Apply realistic transaction costs and slippage
   - Track position P&L and risk metrics

## 🔧 Key Features

### Advanced Options Pricing
- **Black-Scholes Implementation**: Full Greeks calculation (delta, gamma, theta, vega, rho)
- **Spread Pricing**: Bull and bear call spread valuation with profit/loss analysis
- **Implied Volatility**: Surface construction and smile modeling
- **Strike Optimization**: Automated optimal strike selection based on target delta

### Sophisticated Risk Management
- **Portfolio Limits**: Delta, gamma, vega, theta exposure limits
- **Concentration Management**: Limits by expiry, strike, and strategy type
- **VaR Calculation**: Value-at-Risk and stress testing
- **Real-time Monitoring**: Continuous risk alert system

### Market Making Strategy
- **Market Regime Detection**: VIX-based volatility regime classification
- **Dynamic Parameter Adjustment**: Strategy adaptation to market conditions
- **Opportunity Scoring**: Multi-factor scoring system for spread selection
- **Position Management**: Automated profit-taking and loss-cutting rules

### Comprehensive Backtesting
- **Misbuffet Integration**: Professional backtesting framework
- **Performance Analytics**: Sharpe ratio, max drawdown, win rate analysis
- **Transaction Cost Modeling**: Realistic commission and slippage modeling
- **MLflow Tracking**: Experiment tracking and result persistence

## 📊 Configuration Parameters

### SPX Configuration
```python
DEFAULT_CONFIG = {
    # SPX Settings
    'underlying_symbol': 'SPX',
    'underlying_exchange': 'CBOE',
    'underlying_currency': 'USD',
    
    # Call Spread Parameters
    'spread_type': 'bull_call_spread',  # or 'bear_call_spread'
    'default_dte_range': (7, 45),       # Days to expiration range
    'default_delta_range': (0.15, 0.45), # Target delta range
    'max_spread_width': 50,              # Maximum spread width
    
    # Risk Management
    'max_position_size': 10,             # Maximum positions
    'max_daily_loss': 5000,              # Maximum daily loss USD
    'max_gamma_exposure': 1000,          # Maximum gamma exposure
    'min_time_to_expiry': 7,             # Close positions before expiry
    
    # Market Data
    'historical_data_duration': '6 M',   # Data history to import
    'bar_size_setting': '5 mins',        # Data granularity
}
```

### Trading Configuration
```python
trading_config = {
    'max_position_size': 10,
    'max_daily_loss': 5000,
    'commission_per_contract': 0.65,
    'trading_hours': {
        'start': '09:30',
        'end': '16:00',
        'timezone': 'US/Eastern'
    },
}
```

## 🚀 Usage Examples

### Basic Usage
```python
from market_making_SPX_call_spread_project.project_manager import MarketMakingSPXCallSpreadProjectManager

# Initialize manager
manager = MarketMakingSPXCallSpreadProjectManager()

# Run complete pipeline
results = manager.run(
    initial_capital=100000,
    start_date='2023-01-01',
    end_date='2024-12-31',
    check_data=True,
    import_data=True,
    run_backtest=True
)

# Access results
if results['success']:
    performance = results['stages']['backtest_stage']['results']['performance_metrics']
    print(f"Total Return: {performance['total_return']:.2%}")
    print(f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {performance['max_drawdown']:.2%}")
```

### Data Import Only
```python
# Check and import SPX data only
results = manager.run(
    check_data=True,
    import_data=True,
    run_backtest=False
)

data_stage = results['stages']['data_stage']
print(f"Data available: {data_stage['data_available']}")
if data_stage.get('import_results'):
    print(f"Bars imported: {data_stage['import_results']['bars_imported']}")
```

### Strategy Testing
```python
# Test strategy components individually
from market_making_SPX_call_spread_project.strategy.market_making_strategy import CallSpreadMarketMakingStrategy
from market_making_SPX_call_spread_project.config import DEFAULT_CONFIG

strategy = CallSpreadMarketMakingStrategy(DEFAULT_CONFIG)

# Analyze market conditions
market_data = {'spx_price': 4500, 'vix': 20}
analysis = strategy.analyze_market_conditions(market_data)
print(f"Market regime: {analysis['regime']}")

# Generate opportunities
opportunities = strategy.generate_spread_opportunities(
    spx_price=4500,
    option_chain={'expiries': ['2024-01-19'], 'strikes': [4450, 4475, 4500, 4525, 4550]},
    market_analysis=analysis
)
print(f"Generated {len(opportunities)} opportunities")
```

## 🔍 Data Integration

### SPX Data Sources
- **Primary Source**: Interactive Brokers API via `MarketData.get_index_historical_data()`
- **Symbol**: SPX (S&P 500 Index)
- **Exchange**: CBOE (Chicago Board Options Exchange)
- **Data Types**: OHLCV bars, implied volatility, option chains

### Data Verification Process
1. **Database Check**: Query existing SPX records
2. **Coverage Analysis**: Identify gaps in historical data
3. **Quality Validation**: Check for anomalies and outliers
4. **Automatic Import**: Fetch missing data via IBKR API
5. **Factor Storage**: Convert to factor system for unified access

### Factor System Integration
- **Price Factors**: OHLCV data stored as individual factors
- **Technical Factors**: Moving averages, RSI, MACD, Bollinger Bands
- **Volatility Factors**: Historical volatility, ATR, Garman-Klass estimator
- **Market Factors**: VIX integration, term structure slopes

## ⚡ Performance Optimization

### Efficient Data Access
- **Database Indexing**: Optimized queries for factor retrieval
- **Caching Strategy**: In-memory caching of frequently accessed data
- **Batch Processing**: Bulk operations for factor calculations
- **Lazy Loading**: On-demand data loading for large datasets

### Strategy Optimization
- **Vectorized Calculations**: NumPy-based Greeks calculations
- **Parallel Processing**: Multi-threaded opportunity scanning
- **Smart Filtering**: Early elimination of non-viable opportunities
- **Risk Pre-screening**: Fast risk checks before detailed analysis

### Backtesting Performance
- **Simulation Optimization**: Efficient event-driven simulation
- **Memory Management**: Controlled memory usage for long backtests
- **Progress Tracking**: Real-time progress monitoring
- **Result Caching**: Persistent result storage for analysis

## 📈 Expected Outcomes

### Performance Targets
- **Annual Return**: Target 8-12% after transaction costs
- **Sharpe Ratio**: Target >1.0 for risk-adjusted performance
- **Maximum Drawdown**: Keep under 15% for capital preservation
- **Win Rate**: Target 60-70% winning trades
- **Volatility**: Target 10-15% annual volatility

### Risk Metrics
- **VaR (95%)**: Daily Value-at-Risk under 2% of capital
- **Expected Shortfall**: Conditional VaR under 3% of capital
- **Maximum Leverage**: Keep gross exposure under 200% of capital
- **Concentration**: No single expiry >30%, no single strike >20%

### Strategy Benefits
1. **Consistent Income**: Regular premium collection from spread sales
2. **Defined Risk**: Limited maximum loss per spread position
3. **Market Neutral**: Reduced directional market exposure
4. **Liquidity Provision**: Contributing to market efficiency
5. **Scalability**: Strategy can be scaled with available capital

## 🔮 Future Enhancements

### Phase 1: Advanced Modeling (Next 3 months)
- **Machine Learning Integration**: ML-based opportunity scoring
- **Sentiment Analysis**: News and social media sentiment factors
- **Microstructure Models**: Order book and flow analysis
- **Alternative Volatility Models**: GARCH, stochastic volatility

### Phase 2: Multi-Asset Expansion (6 months)
- **Index Options**: Extend to QQQ, IWM, other index options
- **ETF Options**: Single-name ETF option market making
- **Cross-Asset Spreads**: Correlation-based spread strategies
- **Currency Options**: FX option market making capabilities

### Phase 3: Real-Time Trading (12 months)
- **Live Data Feeds**: Real-time market data integration
- **Order Management**: Direct broker connectivity
- **Risk Monitoring**: Real-time risk dashboard
- **Performance Attribution**: Live P&L decomposition

### Phase 4: Advanced Strategies (18 months)
- **Volatility Arbitrage**: Cross-term structure trading
- **Delta-Neutral Strategies**: Market-neutral portfolio construction
- **Exotic Options**: Barrier options, Asian options market making
- **Systematic Hedging**: Dynamic delta and gamma hedging

## 🛠️ Technical Implementation

### Key Classes Overview

#### `MarketMakingSPXCallSpreadProjectManager`
- **Purpose**: Main orchestrator for the entire pipeline
- **Key Methods**: `run()`, `_run_data_stage()`, `_run_backtest_stage()`
- **Integration**: MLflow tracking, database management, component coordination

#### `CallSpreadPricingEngine`
- **Purpose**: Options pricing and Greeks calculation
- **Key Methods**: `black_scholes_call()`, `price_call_spread()`, `find_optimal_strikes()`
- **Features**: Full Black-Scholes implementation, spread optimization

#### `CallSpreadMarketMakingStrategy`
- **Purpose**: Core trading strategy logic
- **Key Methods**: `analyze_market_conditions()`, `generate_spread_opportunities()`
- **Features**: Market regime detection, opportunity generation, position management

#### `RiskManager`
- **Purpose**: Comprehensive risk management system
- **Key Methods**: `check_position_limits()`, `calculate_portfolio_risk_metrics()`
- **Features**: Real-time monitoring, stress testing, limit enforcement

#### `VolatilityModel`
- **Purpose**: Volatility surface modeling and forecasting
- **Key Methods**: `build_implied_volatility_surface()`, `forecast_volatility()`
- **Features**: Surface interpolation, term structure analysis

## 📚 Dependencies

### Required Packages
```python
# Core dependencies
import numpy as np           # Numerical computations
import pandas as pd          # Data manipulation
import scipy as sp           # Scientific computing
from sklearn import *        # Machine learning

# Options pricing
from scipy.stats import norm # Black-Scholes distributions
from scipy.optimize import * # Optimization routines

# Database and infrastructure
from src.application.services.database_service import DatabaseService
from src.application.services.api_service.ibkr_service.market_data import MarketData

# Experiment tracking
import mlflow                # Experiment tracking
import mlflow.sklearn        # ML model tracking
```

### External Services
- **Interactive Brokers**: Market data and option chain feeds
- **Database**: PostgreSQL/SQLite for factor storage
- **MLflow**: Experiment tracking and model management

## 🎛️ Monitoring & Maintenance

### Key Monitoring Metrics
- **Data Freshness**: Last SPX data update timestamp
- **System Health**: Component initialization success rates
- **Strategy Performance**: Real-time P&L and risk metrics
- **Model Accuracy**: Pricing model vs market price deviations

### Regular Maintenance Tasks
- **Data Cleanup**: Remove old/stale data beyond retention period
- **Model Retraining**: Update volatility and pricing models
- **Configuration Updates**: Adjust parameters based on market conditions
- **Performance Review**: Monthly strategy performance analysis

### Alert System
- **Risk Alerts**: Position limit breaches, large losses
- **Data Alerts**: Missing data, stale prices, API failures
- **Performance Alerts**: Drawdown thresholds, poor performance
- **System Alerts**: Component failures, resource constraints

---

## 📋 Quick Start Checklist

### Initial Setup
- [ ] Verify database connectivity and schema
- [ ] Configure IBKR API credentials and permissions
- [ ] Test MLflow tracking setup
- [ ] Validate configuration parameters

### Data Preparation
- [ ] Check existing SPX data in database
- [ ] Import historical SPX data via IBKR API
- [ ] Verify data quality and completeness
- [ ] Create initial factor definitions

### Strategy Testing
- [ ] Run strategy components in isolation
- [ ] Validate pricing engine accuracy
- [ ] Test risk management limits
- [ ] Verify backtest functionality

### Production Readiness
- [ ] Complete end-to-end pipeline test
- [ ] Review all configuration parameters
- [ ] Set up monitoring and alerting
- [ ] Document operational procedures

The SPX Call Spread Market Making Project represents a production-ready, institutional-quality options trading system designed for consistent performance in dynamic market conditions. Its modular architecture ensures maintainability while advanced risk management provides capital protection in volatile markets.