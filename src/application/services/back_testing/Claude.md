# QuantConnect Lean Python Implementation

## Overview

This is a comprehensive Python implementation of the QuantConnect Lean algorithmic trading engine, providing a complete framework for backtesting and live trading algorithmic strategies. The implementation follows Domain-Driven Design (DDD) principles and provides enterprise-grade functionality for quantitative trading.

## How to Use the Backtesting Tool

### Execution Flow
The backtesting tool follows a structured execution flow similar to the QuantConnect Lean engine:

1. **Launcher** (`launcher/`) - System bootstrap and configuration
2. **Engine** (`engine/`) - Main backtesting and live trading engine
3. **Handlers** - Various handlers for data, results, transactions, etc.
4. **Algorithm Factory** (`algorithm_factory/`) - Algorithm loading and compilation
5. **Algorithm** (`algorithm_framework/`) - Specific algorithm implementations
6. **Algorithm Class** (`algorithm/`) - Base algorithm classes
7. **Interfaces** (`common/interfaces/`) - Core contracts and interfaces

### Step-by-Step Usage

#### 1. Configure Your Environment
```bash
# Set up environment variables
export QC_API_KEY="your_api_key"
export QC_API_SECRET="your_api_secret"
export DATA_FOLDER="/path/to/data"
export RESULTS_FOLDER="/path/to/results"
```

#### 2. Create Your Algorithm
Create your algorithm in the `algorithm_framework/` folder, inheriting from the base algorithm class:

```python
from back_testing.algorithm_framework.portfolio import BlackLittermanPortfolioOptimizationAlgorithm
from back_testing.common.interfaces import IAlgorithm

class MyTradingAlgorithm(IAlgorithm):
    def initialize(self):
        # Algorithm initialization
        pass
    
    def on_data(self, data):
        # Trading logic
        pass
```

#### 3. Configure the Launcher
```python
from back_testing.launcher import Launcher, LauncherConfiguration

config = LauncherConfiguration()
config.algorithm = MyTradingAlgorithm
config.start_date = datetime(2020, 1, 1)
config.end_date = datetime(2021, 1, 1)
config.initial_capital = 100000
```

#### 4. Run the Backtest
```python
launcher = Launcher()
result = launcher.run(config)
```

### Architecture Flow Details

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                LAUNCHER                                          │
│  • System bootstrap and configuration                                           │
│  • Command line interface                                                       │
│  • Configuration management                                                      │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 ENGINE                                           │
│  • Main backtesting orchestrator                                                │
│  • Handler coordination                                                          │
│  • Algorithm lifecycle management                                               │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               HANDLERS                                           │
│  • Data Feed Handlers (data/)                                                   │
│  • Result Handlers (results/)                                                   │
│  • Transaction Handlers (transactions/)                                         │
│  • Algorithm Handlers (algorithm management/)                                   │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ALGORITHM FACTORY                                      │
│  • Algorithm loading and compilation                                            │
│  • Algorithm validation                                                          │
│  • Algorithm instance creation                                                   │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ALGORITHM FRAMEWORK                                      │
│  • Specific algorithm implementations                                           │
│  • Portfolio construction models                                                │
│  • Risk management models                                                       │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ALGORITHM CLASS                                        │
│  • Base algorithm classes                                                       │
│  • Common algorithm utilities                                                   │
│  • Security and order management                                                │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMMON INTERFACES                                        │
│  • IAlgorithm - Core algorithm interface                                       │
│  • IDataFeed - Data feed interface                                             │
│  • IResultHandler - Result handling interface                                  │
│  • All other core contracts                                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Architecture

The framework is built using a modular, handler-based architecture that separates concerns and provides flexibility for different trading scenarios:

```
src/application/services/back_testing/
├── common/          # Core interfaces and shared utilities
├── data/           # Data acquisition and management
├── engine/         # Main backtesting and live trading engine
├── algorithm_factory/ # Algorithm loading and compilation
├── algorithm_framework/ # Specific algorithm implementations
├── api/            # REST API client for QuantConnect platform
├── launcher/       # System bootstrap and configuration
├── optimizer/      # Parameter optimization algorithms
├── optimizer_launcher/ # Distributed optimization orchestration
└── algorithm/      # Algorithm base classes and utilities
```

## Core Modules

### 1. Common Module

The foundation module providing core interfaces, data structures, and shared utilities.

**Key Components:**
- **Interfaces**: 17+ core interfaces (`IAlgorithm`, `IDataFeed`, `IResultHandler`, `IApi`)
- **Data Types**: Market data structures (`BaseData`, `TradeBar`, `QuoteBar`, `Tick`, `Slice`)
- **Enumerations**: 15+ enums for resolution, security types, order types, etc.
- **Symbol System**: Symbol class with caching and multi-asset support
- **Time Utilities**: Market hours, time zones, trading calendars
- **Securities**: Portfolio management, holdings tracking, security objects
- **Orders**: Complete order system with 6 order types and OrderTicket management

```python
from back_testing.common import IAlgorithm, BaseData, Symbol, Resolution
```

### 2. Data Module

Handles all aspects of market data acquisition, formatting, and consumption.

**Key Components:**
- **Data Feeds**: Live & backtesting feeds with real-time processing
- **Subscription Management**: Dynamic subscriptions with synchronization
- **Data Readers**: Support for Lean, CSV, JSON, Alpha Streams formats
- **History Providers**: File system, brokerage, composite providers
- **Data Management**: Orchestration with BacktestDataManager & LiveDataManager
- **Queue Handlers**: Fake, WebSocket, REST API data sources
- **Utilities**: Normalization, caching, file format conversion

```python
from back_testing.data import DataFeed, SubscriptionManager, HistoryProvider
```

### 3. Engine Module

The core backtesting and live trading engine with handler-based architecture.

**Key Components:**
- **LeanEngine**: Main orchestrator engine
- **Data Feed Handlers**: FileSystem, Live, Backtesting feeds
- **Transaction Handlers**: Order processing with simulation and live brokerage
- **Result Handlers**: Performance tracking and reporting
- **Setup Handlers**: Algorithm initialization and configuration
- **Real-time Handlers**: Time management and event scheduling
- **Algorithm Handlers**: Algorithm lifecycle management

```python
from back_testing.engine import LeanEngine, BacktestingDataFeed, BacktestingTransactionHandler
```

### 4. Algorithm Factory Module

Manages algorithm creation, loading, and compilation.

**Key Components:**
- **AlgorithmFactory**: Main factory with caching and validation
- **Algorithm Loaders**: File, module, source code loading with AST parsing
- **PythonCompiler**: Compilation with syntax checking and linting
- **AlgorithmManager**: Lifecycle management and monitoring
- **Configuration**: AlgorithmNodePacket for deployment

```python
from back_testing.algorithm_factory import AlgorithmFactory, PythonCompiler
```

### 5. API Module

REST API client for QuantConnect platform integration.

**Key Components:**
- **Authentication**: API key (HMAC-SHA256) + OAuth2 with auto-refresh
- **API Clients**: Project, Backtest, Live Algorithm, Data, Node managers
- **Models**: 25+ DTOs with validation for projects, backtests, results
- **Serialization**: JSON utilities with dataclass support
- **Exception Handling**: 20+ specialized exception types

```python
from back_testing.api import QuantConnectApiClient, ApiKeyAuthenticationProvider
```

### 6. Launcher Module

System bootstrap and configuration management.

**Key Components:**
- **Configuration**: Multi-source loading (JSON, env vars, CLI)
- **Command Line**: Comprehensive CLI with validation
- **Handler Coordinators**: System and algorithm handler management
- **Main Launcher**: Orchestrator with initialization and error handling
- **Signal Handling**: Graceful shutdown for SIGINT/SIGTERM

```python
from back_testing.launcher import Launcher, ConfigurationProvider
```

### 7. Optimizer Module

Parameter optimization algorithms for strategy tuning.

**Key Components:**
- **Genetic Algorithm**: Full GA with population management, selection strategies
- **Grid Search**: Exhaustive parameter space exploration
- **Random Search**: Intelligent sampling with exploration/exploitation balance
- **Parameter Management**: Complete parameter system with constraint validation
- **Result Management**: Comprehensive result system with 20+ trading metrics

```python
from back_testing.optimizer import GeneticOptimizer, GridSearchOptimizer, OptimizerFactory
```

### 8. Optimizer Launcher Module

Distributed optimization orchestration across multiple worker nodes.

**Key Components:**
- **Campaign Management**: Complete optimization lifecycle orchestration
- **Worker Management**: Local, Docker, and cloud worker support
- **Result Coordination**: Real-time result collection and aggregation
- **Configuration**: Advanced configuration with validation
- **Fault Tolerance**: Automatic retry and error recovery

```python
from back_testing.optimizer_launcher import OptimizerLauncher, WorkerManager
```

## Getting Started

### Basic Usage

```python
from back_testing import *

# Create a simple algorithm
class MyAlgorithm(IAlgorithm):
    def initialize(self):
        self.add_equity("SPY", Resolution.DAILY)
    
    def on_data(self, data):
        if not self.securities["SPY"].invested:
            self.market_order("SPY", 100)

# Set up and run backtest
config = LauncherConfiguration()
config.algorithm = MyAlgorithm
config.start_date = datetime(2020, 1, 1)
config.end_date = datetime(2021, 1, 1)
config.initial_capital = 100000

launcher = Launcher()
result = launcher.run(config)
```

### Advanced Usage with Optimization

```python
from back_testing.optimizer import *

# Define optimization parameters
parameters = [
    OptimizationParameter("fast_period", int, 5, 50),
    OptimizationParameter("slow_period", int, 20, 200),
    OptimizationParameter("threshold", float, 0.01, 0.1)
]

# Create optimizer
optimizer = GeneticOptimizer(
    population_size=50,
    generations=100,
    mutation_rate=0.1
)

# Run optimization
results = optimizer.optimize(MyAlgorithm, parameters)
best_params = results.best_parameters
```

## Configuration

### Environment Variables

```bash
# QuantConnect API credentials
export QC_API_KEY="your_api_key"
export QC_API_SECRET="your_api_secret"

# Data source configuration
export DATA_FOLDER="/path/to/data"
export RESULTS_FOLDER="/path/to/results"

# Engine configuration
export ENGINE_MODE="backtesting"  # or "live"
export LOG_LEVEL="INFO"
```

### Configuration File (config.json)

```json
{
  "algorithm": {
    "name": "MyAlgorithm",
    "language": "Python",
    "location": "algorithms/my_algorithm.py"
  },
  "backtest": {
    "start_date": "2020-01-01",
    "end_date": "2021-01-01",
    "initial_capital": 100000,
    "benchmark": "SPY"
  },
  "data": {
    "data_folder": "/data",
    "resolution": "Daily",
    "market": "USA"
  },
  "optimizer": {
    "enabled": true,
    "algorithm": "genetic",
    "population_size": 50,
    "generations": 100
  }
}
```

## API Reference

### Core Interfaces

#### IAlgorithm
```python
class IAlgorithm(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Called once at start to setup initial state."""
        
    @abstractmethod
    def on_data(self, data: Slice) -> None:
        """Called when new market data arrives."""
        
    @abstractmethod
    def on_order_event(self, order_event: OrderEvent) -> None:
        """Called when an order event occurs."""
```

#### IDataFeed
```python
class IDataFeed(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the data feed."""
        
    @abstractmethod
    def create_subscription(self, symbol: Symbol, resolution: Resolution) -> SubscriptionDataConfig:
        """Create a data subscription."""
```

### Data Types

#### BaseData
```python
@dataclass
class BaseData:
    symbol: Symbol
    time: datetime
    end_time: datetime
    value: Decimal
    data_type: str = "BaseData"
```

#### TradeBar
```python
@dataclass
class TradeBar(BaseData):
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
```

### Order Management

#### Market Order
```python
def market_order(symbol: str, quantity: int) -> OrderTicket:
    """Place a market order."""
    
def limit_order(symbol: str, quantity: int, price: Decimal) -> OrderTicket:
    """Place a limit order."""
    
def stop_market_order(symbol: str, quantity: int, stop_price: Decimal) -> OrderTicket:
    """Place a stop market order."""
```

## Performance Considerations

### Memory Management
- **Data Caching**: Configurable cache sizes for historical data
- **Object Pooling**: Reusable objects for high-frequency operations
- **Garbage Collection**: Explicit cleanup in long-running backtests

### Execution Speed
- **Concurrent Processing**: Multi-threaded data processing
- **Vectorized Operations**: NumPy/Pandas integration for calculations
- **JIT Compilation**: Optional Numba acceleration for hot paths

### Scalability
- **Distributed Computing**: Multi-node optimization support
- **Cloud Integration**: AWS/Azure worker node support
- **Resource Monitoring**: Memory and CPU usage tracking

## Testing

### Unit Tests
```bash
# Run all tests
python -m unittest discover tests

# Run specific module tests
python -m unittest tests.test_engine
python -m unittest tests.test_optimizer
```

### Integration Tests
```bash
# Run integration tests
python -m unittest tests.integration.test_full_backtest
```

### Performance Tests
```bash
# Run performance benchmarks
python tests/performance/benchmark_engine.py
```

## Advanced Features

### Custom Data Sources
```python
class CustomDataReader(BaseDataReader):
    def read(self, symbol: Symbol, resolution: Resolution) -> Iterator[BaseData]:
        # Custom data reading logic
        pass
```

### Custom Indicators
```python
class CustomIndicator(IndicatorBase):
    def update(self, input_data: BaseData) -> None:
        # Custom indicator calculation
        pass
```

### Risk Management
```python
class RiskManager:
    def can_submit_order(self, order: Order) -> bool:
        # Risk validation logic
        pass
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ /app/src/
WORKDIR /app

CMD ["python", "-m", "back_testing.launcher"]
```

### Cloud Deployment
- **AWS Lambda**: Serverless algorithm execution
- **Google Cloud Run**: Containerized backtesting
- **Azure Functions**: Event-driven trading

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Data Issues**: Verify data folder permissions and format
3. **Memory Issues**: Adjust cache sizes and batch processing
4. **Performance**: Enable JIT compilation and vectorization

### Debugging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed engine logging
engine.set_log_level(LogLevel.DEBUG)
```

### Support

- **Documentation**: Full API documentation available
- **Examples**: Comprehensive example algorithms included
- **Community**: Active community support and contributions

## License

This implementation is provided under the same license terms as the original QuantConnect Lean project.

## Contributing

Contributions are welcome! Please follow the existing code style and include tests for new features.

---

*This implementation provides a complete, production-ready algorithmic trading framework with enterprise-grade features and performance optimization.*