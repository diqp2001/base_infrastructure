# CLAUDE.md – Test Base Project Manager

## 🎯 Purpose

The **Test Base Project Manager** is a comprehensive trading system that combines sophisticated spatiotemporal momentum modeling with robust factor creation, data storage, and backtesting capabilities. This project serves as a hybrid architecture that brings together the best aspects of three existing project managers to create a complete end-to-end trading pipeline.

## 🧬 Inspiration & Architecture Fusion

This project strategically combines elements from three foundational managers:

### 1. **Spatiotemporal Momentum Manager** (Core Logic & Flow)
- **Primary Inspiration**: Main algorithmic logic and pipeline architecture
- **Key Elements Adopted**:
  - Multi-asset time series processing with `[timesteps, features, assets]` input shape
  - TFT (Temporal Fusion Transformer) and MLP model management
  - Multivariate/univariate tensor creation and train-validation-test splitting
  - Momentum-based feature engineering (deep momentum, MACD signals)
  - Rolling window training with temporal integrity (no lookahead bias)
  - Advanced loss functions: Sharpe loss, L1 regularization, turnover penalty

### 2. **Test Project Factor Creation** (Data Extraction & Storage)
- **Enhancement Purpose**: Robust data management and factor architecture
- **Key Elements Integrated**:
  - Comprehensive factor definition framework (price, volume, technical indicators)
  - Database-backed factor storage with validation rules
  - CSV data ingestion and historical data population
  - Factor repository pattern with bulk operations
  - Entity-factor relationship management
  - Real-time factor value calculation and persistence

### 3. **Test Project Backtest** (Backtesting & Web Integration)
- **Enhancement Purpose**: Live backtesting engine with web interface
- **Key Elements Incorporated**:
  - Misbuffet backtesting framework integration
  - Web interface for real-time backtest monitoring
  - Progress tracking and result visualization
  - Black-Litterman portfolio optimization
  - Algorithm lifecycle management (initialization, data handling, execution)
  - Performance analytics and result persistence

## 🏗️ Overall Architecture & Folder Structure

```
src/application/managers/project_managers/test_base_project/
├── CLAUDE.md                           # This documentation file
├── __init__.py                         # Package initialization
├── config.py                           # Database and system configuration
├── test_base_project_manager.py        # Main manager class
├── 
├── data/                               # Data processing components
│   ├── __init__.py
│   ├── data_loader.py                  # CSV/database data loading
│   ├── feature_engineer.py            # Spatiotemporal feature creation
│   └── factor_manager.py               # Factor definition and storage
│
├── models/                             # ML model components
│   ├── __init__.py
│   ├── spatiotemporal_model.py         # TFT/MLP model wrapper
│   ├── model_trainer.py               # Training pipeline
│   └── tensor_splitter.py              # Multivariate/univariate splitting
│
├── strategy/                           # Trading strategy components
│   ├── __init__.py
│   ├── momentum_strategy.py            # Core momentum strategy
│   ├── portfolio_optimizer.py          # Black-Litterman optimization
│   └── signal_generator.py             # ML-based signal generation
│
├── backtesting/                        # Backtesting engine components
│   ├── __init__.py
│   ├── backtest_engine.py              # Misbuffet integration
│   ├── algorithm.py                    # QCAlgorithm implementation
│   ├── engine_config.py                # Backtest configuration
│   └── launch_config.py                # Launcher configuration
│
├── web/                                # Web interface components
│   ├── __init__.py
│   ├── web_interface.py                # Flask-based monitoring
│   ├── progress_tracker.py             # Real-time progress updates
│   └── result_visualizer.py            # Performance charts
│
└── utils/                              # Utility components
    ├── __init__.py
    ├── loss_functions.py               # Custom loss functions (Sharpe, turnover)
    ├── validators.py                   # Data validation utilities
    └── performance_metrics.py          # Performance calculation utilities
```

## 🔄 Project Flow & Pipeline Stages

### Stage 1: **Data Loading & Factor Creation**
*Inspired by: test_project_factor_creation*

1. **Entity Creation**
   - Initialize database tables for companies and currencies
   - Create CompanyShare entities for target universe (AAPL, MSFT, AMZN, GOOGL)
   - Set up factor definitions (OHLCV, technical indicators, momentum features)

2. **Historical Data Ingestion**
   - Load CSV stock data from file system
   - Populate factor values in database
   - Create factor validation rules
   - Establish factor-entity relationships

3. **Feature Engineering**
   - Generate deep momentum features (multi-timeframe returns)
   - Calculate MACD signals across different periods
   - Create volatility and technical indicators
   - Store engineered features as factors

### Stage 2: **Model Training & Spatiotemporal Processing**
*Inspired by: spatiotemporal_momentum_manager*

4. **Data Preprocessing**
   - Retrieve factor data for model training
   - Create multivariate/univariate tensor structures
   - Apply temporal train-validation-test splits
   - Handle missing data and scaling

5. **Model Training**
   - Train TFT models for complex temporal patterns
   - Train MLP models for simpler feature relationships
   - Use custom loss functions (Sharpe ratio optimization)
   - Apply regularization (L1, turnover penalty)

6. **Model Validation**
   - Rolling window cross-validation
   - Performance evaluation on validation sets
   - Model selection and hyperparameter optimization

### Stage 3: **Backtesting & Web Integration**
*Inspired by: test_project_backtest*

7. **Algorithm Implementation**
   - Create QCAlgorithm with spatiotemporal model integration
   - Implement signal generation from trained models
   - Apply Black-Litterman portfolio optimization
   - Execute trades based on optimized weights

8. **Backtest Execution**
   - Launch Misbuffet backtesting engine
   - Run algorithm with historical data
   - Track performance and risk metrics
   - Handle transaction costs and slippage

9. **Web Interface & Monitoring**
   - Start Flask web interface
   - Provide real-time progress updates
   - Display performance charts and metrics
   - Enable parameter adjustment and re-runs

## 🔧 Component Integration & Reused Elements

### From Spatiotemporal Momentum Manager:
- **Reused**: `SpatioTemporalMomentumManager` class architecture
- **Adapted**: Feature engineering methods (`add_deep_momentum_features`, `add_macd_signal_features`)
- **Enhanced**: Model training pipeline with factor-based data retrieval
- **Integrated**: Loss functions (`sharpe_loss`, `reg_turnover`, `reg_l1`)

### From Test Project Factor Creation:
- **Reused**: Factor repository pattern and database schema
- **Adapted**: Entity creation with bulk operations
- **Enhanced**: Factor definitions to include spatiotemporal features
- **Integrated**: Real-time factor calculation during backtesting

### From Test Project Backtest:
- **Reused**: Misbuffet framework integration
- **Adapted**: Algorithm class with ML model integration
- **Enhanced**: Web interface with factor system monitoring
- **Integrated**: Performance tracking with factor-based analytics

### MLflow Experiment Tracking Integration:
- **Experiment Management**: Automatic experiment creation and run management
- **Parameter Logging**: Complete simulation parameters (tickers, dates, model types, capital)
- **Metrics Tracking**: Performance metrics (Sharpe ratio, returns, drawdown, execution time)
- **Artifact Storage**: Model info, simulation results, and configuration files
- **Stage-wise Tracking**: Factor setup, model training, and backtesting metrics
- **Error Handling**: Proper MLflow run cleanup and error state logging

## 📊 Expected Functions & Classes

### Core Manager Class
```python
class TestBaseProjectManager(ProjectManager):
    """
    Main project manager combining spatiotemporal modeling,
    factor creation, and backtesting capabilities.
    """
    def __init__(self)
    def setup_factor_system(self) -> Dict[str, Any]
    def create_entities_and_factors(self) -> Dict[str, Any]
    def train_spatiotemporal_models(self) -> Dict[str, Any]
    def run_backtest_with_web_interface(self) -> Dict[str, Any]
    def get_comprehensive_results(self) -> Dict[str, Any]
```

### Data Processing Components
```python
class SpatiotemporalDataLoader:
    def load_historical_data_with_factors(self) -> pd.DataFrame
    def prepare_multivariate_tensors(self) -> MultivariateTrainValTestSplitterService
    def create_factor_features(self) -> pd.DataFrame

class FactorEnginedDataManager:
    def populate_momentum_factors(self)
    def calculate_technical_indicators(self)
    def store_engineered_factors(self)
```

### Model Components
```python
class HybridSpatiotemporalModel:
    def train_tft_with_factors(self)
    def train_mlp_with_factors(self)
    def generate_signals_from_factors(self)

class PortfolioOptimizer:
    def apply_black_litterman_with_signals(self)
    def optimize_weights_with_risk_constraints(self)
```

### Backtesting Components
```python
class FactorBacktestAlgorithm(QCAlgorithm):
    def initialize_with_factor_system(self)
    def on_data_with_factor_updates(self)
    def execute_spatiotemporal_strategy(self)

class WebBacktestManager:
    def start_web_interface_with_factors(self)
    def track_factor_performance(self)
    def visualize_spatiotemporal_results(self)
```

## 🔗 Component Connections & Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CSV Data      │───▶│  Factor System   │───▶│ Spatiotemporal  │
│   Loading       │    │  Creation        │    │ Feature Eng.    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │◀───│  Factor Values   │───▶│ Model Training  │
│   Storage       │    │  Population      │    │ (TFT/MLP)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Web Interface  │◀───│  Backtest Engine │◀───│ Signal          │
│  Monitoring     │    │  (Misbuffet)     │    │ Generation      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Future Improvements & Scalability

### Phase 1: Enhanced Model Architecture
- **Multi-Model Ensemble**: Combine TFT, LSTM, and Transformer models
- **Dynamic Feature Selection**: Automated feature importance ranking
- **Regime Detection**: Market state classification for adaptive strategies
- **Alternative Data Integration**: News sentiment, options flow, earnings data

### Phase 2: Advanced Portfolio Management
- **Multi-Asset Support**: Extend beyond equities (FX, commodities, crypto)
- **Risk Parity Integration**: Complement Black-Litterman with risk budgeting
- **Dynamic Hedging**: Automated hedge ratio calculation and execution
- **ESG Factor Integration**: Sustainability and governance factors

### Phase 3: Production Infrastructure
- **Real-Time Data Feeds**: WebSocket integration for live market data
- **Microservices Architecture**: Decompose into scalable services
- **Cloud Deployment**: AWS/GCP with auto-scaling capabilities
- **API Gateway**: RESTful API for external system integration

### Phase 4: Advanced Analytics
- **Reinforcement Learning**: Q-learning for dynamic strategy adaptation
- **Explainable AI**: SHAP/LIME integration for model interpretability
- **Stress Testing**: Monte Carlo scenario analysis
- **Performance Attribution**: Factor-based return decomposition

### Phase 5: User Experience
- **Mobile Application**: iOS/Android trading companion
- **Voice Interface**: Alexa/Google Assistant integration
- **Automated Reporting**: Daily/weekly performance summaries
- **Social Trading**: Strategy sharing and ranking platform

## 🎛️ Configuration & Customization

### Model Configuration
- **TFT Parameters**: Attention heads, hidden dimensions, encoder/decoder lengths
- **Training Parameters**: Learning rates, batch sizes, early stopping criteria
- **Feature Selection**: Enable/disable specific factor groups
- **Risk Parameters**: Maximum position sizes, sector concentration limits

### Backtesting Configuration
- **Time Periods**: Start/end dates, warm-up periods, out-of-sample testing
- **Transaction Costs**: Commission structures, bid-ask spreads, market impact
- **Data Frequency**: Daily, hourly, minute-level backtesting
- **Benchmark Selection**: Custom benchmark or standard indices

### Web Interface Configuration
- **Dashboard Layout**: Customizable chart arrangements and metrics
- **Alert Settings**: Performance thresholds and notification preferences
- **Export Options**: PDF reports, CSV data downloads
- **User Permissions**: Role-based access to different system components

### MLflow Tracking Configuration
- **Experiment Name**: `test_base_project_manager` (configurable)
- **Tracking URI**: Local `mlruns` directory (can be set to remote MLflow server)
- **Auto-logging**: Automatic parameter, metric, and artifact logging for each simulation
- **Run Naming**: Timestamp-based run names with optional custom naming
- **Artifact Types**: JSON results, model information, configuration files
- **Metric Categories**: Performance metrics, timing metrics, success/failure indicators

---

## 📈 Expected Outcomes

This integrated system will provide:

1. **Robust Factor Infrastructure**: Scalable factor creation, storage, and retrieval
2. **Advanced ML Models**: State-of-the-art spatiotemporal modeling capabilities  
3. **Professional Backtesting**: Industry-standard backtesting with realistic constraints
4. **Real-Time Monitoring**: Web-based interface for live system monitoring
5. **Comprehensive Analytics**: Detailed performance attribution and risk analysis
6. **Production Readiness**: Architecture designed for scaling to live trading
7. **Experiment Tracking**: MLflow integration for reproducible simulation runs and model versioning

The Test Base Project Manager represents a significant evolution from its constituent components, creating a unified platform that bridges research, development, and production trading system requirements.

---

## 📊 MLflow Integration Usage

### Basic Usage
```python
# Initialize the manager (MLflow setup happens automatically)
manager = TestBaseProjectManager()

# Run simulation with automatic MLflow tracking
results = manager.run(
    tickers=['AAPL', 'MSFT', 'GOOGL'],
    initial_capital=100000,
    model_type='both',
    launch_web_interface=True
)

# All parameters, metrics, and artifacts are automatically logged
```

### Accessing MLflow UI
```bash
# View experiment results in MLflow UI
mlflow ui --backend-store-uri ./mlruns

# Navigate to http://localhost:5000 to view experiments
```

### Tracked Information
- **Parameters**: Tickers, capital, model types, dates, configurations
- **Metrics**: Portfolio value, returns, Sharpe ratio, max drawdown, execution time
- **Artifacts**: Simulation results JSON, model information, configuration files
- **Tags**: Run status (success/failed/error), error messages
- **Models**: Trained model artifacts and metadata (when available)