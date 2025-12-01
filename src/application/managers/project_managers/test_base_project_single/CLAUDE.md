# CLAUDE.md – Test Base Project Single Manager

## 🎯 Purpose

The **Test Base Project Single Manager** implements a simple yet effective trading algorithm based on a 200-day moving average strategy. This algorithm compares the last close price to the average price over the previous 200 days and makes directional trading decisions accordingly.

## 📊 Core Algorithm Logic

### Simple 200-Day Moving Average Strategy

The algorithm follows this straightforward logic:

1. **Calculate 200-Day Average**: Computes the average closing price over the last 200 trading days
2. **Price Comparison**: Compares the current/last close price to this 200-day average
3. **Trading Decisions**:
   - **Long Position**: When last close price > 200-day average price
   - **Short Position**: When last close price < 200-day average price

This creates a momentum-based trend-following strategy that aims to:
- Capture upward trends by going long when price is above long-term average
- Capture downward trends by going short when price is below long-term average
- Reduce false signals by using a longer-term (200-day) reference period

### Algorithm Characteristics

- **Strategy Type**: Trend-following momentum strategy
- **Signal Generation**: Binary signals based on price-to-average comparison
- **Lookback Period**: 200 trading days (approximately 8-10 months)
- **Decision Frequency**: Updated daily with new price data
- **Risk Profile**: Medium-term trend exposure with reduced noise from short-term fluctuations

## 🏗️ Overall Architecture & Folder Structure

```
src/application/managers/project_managers/test_base_project_single/
├── CLAUDE.md                           # This documentation file
├── __init__.py                         # Package initialization
├── config.py                           # Database and system configuration
├── test_base_project_manager.py        # Main manager class
├── 
├── data/                               # Data processing components
│   ├── __init__.py
│   ├── data_loader.py                  # CSV/database data loading
│   ├── feature_engineer.py            # Basic feature creation (200-day avg)
│   └── factor_manager.py               # Factor definition and storage
│
├── models/                             # Simple model components
│   ├── __init__.py
│   ├── spatiotemporal_model.py         # Placeholder for compatibility
│   ├── model_trainer.py               # Simple training pipeline
│   └── tensor_splitter.py              # Basic data splitting
│
├── strategy/                           # Trading strategy components
│   ├── __init__.py
│   ├── momentum_strategy.py            # 200-day average strategy
│   ├── portfolio_optimizer.py          # Simple position sizing
│   └── signal_generator.py             # Binary signal generation
│
├── backtesting/                        # Backtesting engine components
│   ├── __init__.py
│   ├── backtest_runner.py              # Misbuffet integration
│   ├── base_project_algorithm.py       # Simple QCAlgorithm implementation
│   ├── engine_config.py                # Backtest configuration
│   └── launch_config.py                # Launcher configuration
│
└── utils/                              # Utility components
    ├── __init__.py
    ├── loss_functions.py               # Basic performance functions
    ├── validators.py                   # Data validation utilities
    └── performance_metrics.py          # Performance calculation utilities
```

## 🔄 Project Flow & Pipeline Stages

### Stage 1: **Data Loading & Factor Creation**
*Factor creation remains the same as other test projects*

1. **Entity Creation**
   - Initialize database tables for companies and currencies
   - Create CompanyShare entities for target universe (AAPL, MSFT, AMZN, GOOGL)
   - Set up factor definitions (OHLCV, basic technical indicators)

2. **Historical Data Ingestion**
   - Load CSV stock data from file system
   - Populate factor values in database (especially closing prices)
   - Create factor validation rules
   - Establish factor-entity relationships

3. **Feature Engineering**
   - Calculate 200-day rolling average of closing prices
   - Store 200-day average as a factor in the database
   - Maintain historical price data for continuous calculation
   - Ensure data integrity and proper handling of missing values

### Stage 2: **Signal Generation**
*Simple rule-based approach*

4. **Price Comparison**
   - Retrieve current closing price from factor system
   - Retrieve 200-day average from factor system or calculate on-the-fly
   - Compare current price to 200-day average
   - Generate binary signals: 1 (long) or 0/-1 (short)

5. **Signal Validation**
   - Ensure sufficient data points (at least 200 days) for reliable average
   - Handle edge cases (market holidays, missing data)
   - Apply basic risk filters (volatility checks, position sizing limits)

### Stage 3: **Backtesting with Misbuffet**
*Same backtesting framework as other test projects*

6. **Algorithm Implementation**
   - Create QCAlgorithm with simple 200-day average logic
   - Implement signal generation within the algorithm's on_data method
   - Apply basic position sizing (equal weight or simple risk-adjusted)
   - Execute trades based on binary signals

7. **Backtest Execution**
   - Launch Misbuffet backtesting engine
   - Run algorithm with historical data
   - Track performance metrics (returns, Sharpe ratio, drawdown)
   - Handle transaction costs and realistic slippage

8. **Results & Analysis**
   - Generate performance reports
   - Compare against buy-and-hold benchmark
   - Analyze signal frequency and accuracy
   - Document key performance statistics

## 🔧 Component Integration & Reused Elements

### From Test Project Factor Creation:
- **Reused**: Factor repository pattern and database schema (unchanged)
- **Adapted**: Entity creation with bulk operations for price data storage
- **Enhanced**: Factor definitions include 200-day rolling average calculation
- **Integrated**: Real-time factor calculation for moving averages during backtesting

### From Test Project Backtest:
- **Reused**: Misbuffet framework integration (unchanged)
- **Adapted**: Algorithm class simplified to use binary rule-based signals
- **Simplified**: No complex ML model integration, just price comparison logic
- **Integrated**: Performance tracking with basic metrics and factor monitoring

### Simplified Architecture Benefits:
- **Reduced Complexity**: No advanced ML models or spatiotemporal processing
- **Faster Execution**: Simple calculations with minimal computational overhead  
- **Easy Debugging**: Straightforward logic makes troubleshooting simple
- **Clear Performance Attribution**: Results directly attributable to 200-day average strategy

## 📊 Expected Functions & Classes

### Core Manager Class
```python
class TestBaseProjectManager(ProjectManager):
    """
    Main project manager implementing simple 200-day average strategy
    with factor creation and Misbuffet backtesting.
    """
    def __init__(self)
    def setup_factor_system(self) -> Dict[str, Any]
    def create_entities_and_factors(self) -> Dict[str, Any]
    def calculate_200_day_averages(self) -> Dict[str, Any]
    def run_backtest_with_misbuffet(self) -> Dict[str, Any]
    def get_performance_results(self) -> Dict[str, Any]
```

### Data Processing Components
```python
class SimpleDataLoader:
    def load_historical_price_data(self) -> pd.DataFrame
    def calculate_moving_averages(self, window: int = 200) -> pd.DataFrame
    def prepare_signal_data(self) -> pd.DataFrame

class MovingAverageFactorManager:
    def populate_price_factors(self)
    def calculate_200_day_averages(self)
    def store_moving_average_factors(self)
```

### Signal Generation Components
```python
class SimpleSignalGenerator:
    def generate_200_day_signals(self) -> Dict[str, int]
    def compare_price_to_average(self, ticker: str) -> int
    def validate_signal_quality(self) -> bool

class BasicPositionSizer:
    def calculate_equal_weights(self) -> Dict[str, float]
    def apply_risk_limits(self) -> Dict[str, float]
```

### Backtesting Components
```python
class BaseProjectAlgorithm(QCAlgorithm):
    """
    Simple QCAlgorithm implementing 200-day average strategy:
    - Long when close > 200-day average
    - Short when close < 200-day average
    """
    def initialize(self)
    def on_data(self, data)
    def calculate_200_day_average(self, ticker: str) -> float
    def generate_trading_signals(self) -> Dict[str, int]
    def execute_trades_from_signals(self, signals: Dict[str, int])

class SimpleBacktestRunner:
    def setup_misbuffet_engine(self)
    def run_200_day_average_backtest(self)
    def track_basic_performance(self)
```

## 🔗 Component Connections & Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CSV Data      │───▶│  Factor System   │───▶│   200-Day       │
│   Loading       │    │  Creation        │    │   Average       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │◀───│  Factor Values   │───▶│ Signal          │
│   Storage       │    │  Population      │    │ Generation      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Performance    │◀───│  Backtest Engine │◀───│ Binary Signals  │
│  Tracking       │    │  (Misbuffet)     │    │ (Long/Short)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Simple Algorithm Flow:
1. **Data Input**: Historical price data loaded from CSV files
2. **Factor Creation**: Store prices and calculate 200-day rolling averages
3. **Signal Generation**: Compare current price to 200-day average
4. **Trading Decision**: Generate binary signals (1=Long, -1=Short)
5. **Execution**: Execute trades through Misbuffet backtesting engine
6. **Performance**: Track and analyze strategy performance

## 🚀 Future Improvements & Scalability

### Phase 1: Strategy Enhancements
- **Multiple Moving Averages**: Add 50-day, 100-day, and other period combinations
- **Adaptive Lookback**: Dynamic adjustment of the 200-day window based on market volatility
- **Signal Filtering**: Add volume confirmation or momentum filters
- **Multi-Timeframe Analysis**: Combine daily signals with weekly/monthly trends

### Phase 2: Risk Management
- **Position Sizing**: Implement volatility-based position sizing
- **Stop Loss Integration**: Add trailing stops or fixed stop-loss levels
- **Correlation Analysis**: Avoid over-concentration in correlated assets
- **Sector Rotation**: Extend strategy to sector-based rotation

### Phase 3: Performance Optimization
- **Real-Time Data Integration**: Connect to live market data feeds
- **Execution Optimization**: Minimize transaction costs and slippage
- **Tax-Aware Trading**: Consider tax implications in signal generation
- **Alternative Assets**: Extend beyond equities to ETFs, bonds, commodities

### Phase 4: Advanced Features
- **Machine Learning Enhancement**: Add ML models to refine the basic signals
- **Regime Detection**: Identify market conditions for strategy adaptation
- **Options Integration**: Use options for hedging and enhanced returns
- **Portfolio Construction**: Advanced portfolio optimization techniques

## 🎛️ Configuration & Customization

### Algorithm Configuration
- **Lookback Window**: 200-day period (adjustable: 100, 150, 250 days)
- **Signal Generation**: Binary signals (long/short) or weighted signals
- **Position Sizing**: Equal weight, volatility-adjusted, or fixed dollar amounts
- **Risk Parameters**: Maximum position sizes, stop-loss levels

### Backtesting Configuration
- **Time Periods**: Start/end dates, warm-up periods (minimum 200 days required)
- **Transaction Costs**: Commission structures, bid-ask spreads, realistic slippage
- **Data Frequency**: Daily backtesting (can be extended to hourly/intraday)
- **Benchmark Selection**: SPY, market benchmark, or buy-and-hold comparison

### Factor System Configuration
- **Price Data**: Close, adjusted close, or OHLC data sources
- **Moving Average**: Simple MA (default) or exponential weighted MA
- **Data Validation**: Missing data handling, outlier detection
- **Storage Options**: Database persistence or in-memory calculations

---

## 📈 Expected Outcomes

This simple system will provide:

1. **Clear Trading Logic**: Transparent, rule-based strategy that's easy to understand
2. **Robust Factor Infrastructure**: Same factor creation and storage as complex systems
3. **Professional Backtesting**: Misbuffet integration with realistic trading constraints
4. **Performance Analytics**: Standard metrics (returns, Sharpe, drawdown, win rate)
5. **Fast Execution**: Minimal computational requirements with quick backtesting
6. **Easy Debugging**: Simple logic makes troubleshooting and optimization straightforward
7. **Baseline Performance**: Foundation for comparing more complex strategies

The Test Base Project Single Manager provides a clean, simple implementation of a classic trading strategy that serves as both a standalone system and a baseline for more advanced approaches.

---

## 💡 Algorithm Summary

### Core Strategy Logic
```python
# Pseudo-code for the 200-day average strategy
def generate_signal(current_price: float, avg_200_day: float) -> int:
    """
    Generate trading signal based on price vs 200-day average comparison
    
    Returns:
        1: Long position (current_price > avg_200_day)
        -1: Short position (current_price < avg_200_day)  
    """
    if current_price > avg_200_day:
        return 1  # Go Long
    else:
        return -1  # Go Short
```

### Key Benefits
- **Trend Following**: Captures major market trends by filtering short-term noise
- **Risk Reduction**: 200-day lookback provides stable, less volatile signals
- **Simplicity**: No complex parameters or model training required
- **Proven Strategy**: Well-documented approach used by professional traders
- **Low Maintenance**: Minimal ongoing adjustments or recalibration needed

This strategy works particularly well in trending markets and provides a solid foundation for understanding systematic trading approaches before moving to more complex algorithms.