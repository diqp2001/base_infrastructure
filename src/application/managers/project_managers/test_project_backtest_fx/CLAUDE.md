# FX Test Project - CLAUDE.md

## 🏗️ FX LightGBM + Mean Reversion Trading System

This module implements a sophisticated **Foreign Exchange (FX) trading algorithm** that combines **Machine Learning predictions** with **Mean Reversion signals** for currency pair trading. The system follows the established `base_infrastructure` architecture patterns while adapting them for FX markets.

---

## 📊 Algorithm Overview

### Core Strategy: `FX_LGBM_MeanReversion_Algorithm`

The algorithm implements a dual-signal approach:

1. **Machine Learning Signal**: Uses LightGBM (with fallbacks to XGBoost/RandomForest) to predict next-day currency direction
2. **Mean Reversion Signal**: Calculates z-scores to identify currencies deviating from their rolling mean
3. **Combined Scoring**: Weighted combination of ML predictions and mean reversion expectations
4. **Portfolio Construction**: Selects top 2 currencies to long and bottom 2 to short

### Key Features

- **Currency Universe**: EUR, GBP, AUD, USD, MXN, JPY, CAD
- **Trading Pairs**: EURUSD, GBPUSD, AUDUSD, USDMXN, USDJPY, USDCAD
- **Retraining Frequency**: Weekly model updates
- **Position Sizing**: Equal-weight allocation (40% max per side)
- **Risk Management**: Built-in leverage and position size limits

---

## 🔧 Technical Implementation

### Project Structure

```
test_project_backtest fx/
├── __init__.py
├── CLAUDE.md                           # This documentation
├── config.py                          # FX-specific configuration
├── engine_config.py                   # Backtesting engine settings
├── launch_config.py                   # Launcher configuration
└── test_project_backtest_manager.py   # Main algorithm and manager
```

### Core Components

#### 1. Algorithm Class: `FX_LGBM_MeanReversion_Algorithm`

**Initialization**:
- Sets up FX pair mappings and securities
- Configures ML model parameters
- Establishes training windows and retraining schedule

**Feature Engineering**:
- `_prepare_features_df()`: Calculates returns, moving averages, RSI, volatility
- `_rsi()`: Implements Relative Strength Index calculation
- `_zscore()`: Computes mean reversion z-scores

**Model Training**:
- `_train_model_for_currency()`: Trains individual currency models
- Supports LightGBM → XGBoost → RandomForest fallback hierarchy
- Uses technical features: return, ma_gap, volatility, RSI

**Signal Generation**:
- ML probability predictions for directional moves
- Mean reversion expectations based on z-scores
- Weighted combination (60% ML, 40% mean reversion)

**Portfolio Management**:
- Ranks currencies by combined score
- Implements long/short selection (2 each)
- Handles USD-base vs USD-quote pair inversions

#### 2. Data Manager: `TestProjectBacktestManager`

**FX Data Loading** (`create_fx_currency_data()`):
- Loads historical FX rates from CSV (1995-2018)
- Converts exchange rates to proper price format
- Creates currency entities in database
- Saves processed data for backtesting engine

**Framework Integration**:
- Integrates with Misbuffet backtesting framework
- Provides real-time progress updates via web interface
- Handles database persistence and retrieval

---

## 📈 Data Requirements

### Source Data

**File**: `data/fx_data/currency_exchange_rates_02-01-1995_-_02-05-2018.csv`

**Format**: Daily exchange rates for 47+ currencies vs USD
- Date column + currency rate columns
- Covers 23+ years of historical data
- Major currencies: EUR, GBP, AUD, JPY, CAD, MXN

**Processing**:
- Inverts rates to create proper FX pricing (1/rate)
- Generates OHLC data from daily rates
- Handles missing data with forward-fill

### Database Schema

**Currency Entities**: Stored as specialized `CompanyShare` entities
- Ticker format: `EURUSD`, `USDJPY`, etc.
- Sector: "Currency"
- Enhanced with FX-specific market data

**Price Tables**: `fx_price_data_{currency}`
- Date, Open, High, Low, Close columns
- Volume set to constant (FX doesn't have traditional volume)

---

## ⚙️ Configuration

### Engine Configuration (`engine_config.py`)

**Backtest Period**: 2000-2015 (allows model warmup)
**Initial Capital**: $100,000
**Benchmark**: EURUSD
**Market**: FX (Foreign Exchange)

**Risk Management**:
- Max leverage: 3.0x (appropriate for FX)
- Max position: 40% (matches algorithm design)
- Transaction costs: 0.5 per trade, 2bp slippage

### Algorithm Parameters

```python
# Feature/Training Settings
lookback_window = 60        # Rolling window for features & zscore
train_window = 252          # Training history (1 year)
retrain_interval = 7 days   # Weekly retraining

# Positioning
n_long = 2                  # Number of currencies to long
n_short = 2                 # Number of currencies to short
target_leverage_per_side = 0.4  # 40% max allocation per side

# Signal Weights
ml_weight = 0.6            # Machine learning signal weight
mr_weight = 0.4            # Mean reversion signal weight
```

---

## 🧠 Algorithm Logic Flow

### 1. Data Processing
```
FX CSV → Rate Inversion → OHLC Generation → Database Storage
```

### 2. Feature Engineering
```
Historical Prices → Returns, MA, RSI, Volatility → Feature Matrix
```

### 3. Model Training (Weekly)
```
Feature Matrix → LightGBM/XGBoost/RF → Direction Predictions
```

### 4. Signal Generation
```
ML Predictions + Z-Score Mean Reversion → Combined Score
```

### 5. Portfolio Construction
```
Ranking → Long/Short Selection → Position Sizing → Order Execution
```

### 6. Risk Management
```
Position Limits → Leverage Control → Transaction Cost Application
```

---

## 🎯 Trading Strategy Details

### Signal Combination Logic

**ML Signal**:
- Predicts probability of positive next-day return
- Normalized to [-1, +1] range where 0 = neutral
- Based on: returns, MA gaps, volatility, RSI

**Mean Reversion Signal**:
- Z-score calculation: `(price - rolling_mean) / rolling_std`
- Positive z-score → expect reversion down → negative signal
- Negative z-score → expect reversion up → positive signal

**Combined Score**:
```python
combined_score = 0.6 * ml_signal + 0.4 * mean_reversion_signal
```

### Position Management

**Currency Selection**:
- Rank all currencies by combined score
- Long top 2 currencies (highest scores)
- Short bottom 2 currencies (lowest scores)

**FX Pair Mapping**:
- EUR/GBP/AUD: Trade via XXXUSD pairs (direct)
- JPY/CAD/MXN: Trade via USDXXX pairs (inverted)
- USD exposure managed implicitly across all pairs

**Position Sizing**:
- Each long position: 20% of portfolio (40% / 2)
- Each short position: 20% of portfolio (40% / 2)
- Total exposure: Up to 80% (40% long + 40% short)

---

## 📊 Performance Considerations

### Backtesting Framework
- Uses established Misbuffet framework
- Incorporates realistic transaction costs
- Handles slippage and market impact
- Supports multiple data sources

### Model Robustness
- Weekly retraining prevents overfitting
- Multiple ML algorithm fallbacks
- Feature engineering based on established indicators
- Mean reversion component reduces ML dependency

### Risk Controls
- Position size limits prevent concentration
- Leverage limits control overall risk
- Regular rebalancing maintains target allocation
- Transaction cost awareness in execution

---

## 🚀 Usage Instructions

### Running the FX Backtest

1. **Data Preparation**: Ensure FX CSV file exists in `data/fx_data/`
2. **Dependencies**: Install required packages (pandas, numpy, lightgbm/xgboost/sklearn)
3. **Execution**: Run the manager to start backtest with web interface

```python
from src.application.managers.project_managers.test_project_backtest_fx.test_project_backtest_manager import TestProjectBacktestManager

# Initialize and run
manager = TestProjectBacktestManager()
result = manager.run()
```

### Configuration Customization

**Algorithm Parameters**: Modify in `FX_LGBM_MeanReversion_Algorithm.initialize()`
**Backtest Period**: Update `engine_config.py` start/end dates
**Currency Universe**: Adjust `currencies` list and `currency_pair_for` mapping
**Risk Limits**: Modify leverage and position size in engine config

---

## 🔮 Future Enhancements

### Immediate Improvements
- [ ] Add more sophisticated feature engineering (momentum, correlations)
- [ ] Implement dynamic position sizing based on volatility
- [ ] Add stop-loss and take-profit levels
- [ ] Include economic indicators as features

### Advanced Features
- [ ] Multi-timeframe analysis (daily + weekly signals)
- [ ] Currency correlation analysis for better pair selection
- [ ] Regime detection for adaptive parameters
- [ ] Real-time data feed integration

### Framework Integration
- [ ] Web dashboard for real-time monitoring
- [ ] Performance attribution analysis
- [ ] Risk decomposition reporting
- [ ] Parameter optimization tools

---

## 📚 References & Dependencies

**Framework Dependencies**:
- `application.services.misbuffet`: Core backtesting framework
- `application.managers`: Database and project management
- `domain.entities`: Financial asset entities

**External Libraries**:
- `lightgbm`: Primary ML algorithm (with fallbacks)
- `pandas/numpy`: Data processing and numerical computations
- `scikit-learn`: Backup ML algorithms and utilities

**Data Sources**:
- Historical FX rates: 1995-2018 daily exchange rates
- 47+ currencies vs USD baseline
- Source: Currency exchange rates dataset

---

*This FX trading system demonstrates the flexibility of the `base_infrastructure` architecture for different asset classes while maintaining code quality and architectural consistency.*