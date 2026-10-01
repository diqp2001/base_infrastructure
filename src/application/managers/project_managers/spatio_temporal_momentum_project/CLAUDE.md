# CLAUDE.md – market_making_SPX_call_spread_project

## Purpose

SPX call spread market making project.  Implements the concrete project-specific logic
that plugs into the reusable infrastructure provided by `misbuffet/`.

---

## Structure

```
market_making_SPX_call_spread_project/
├── config.py                           # DEFAULT_CONFIG, get_config()
├── project_manager.py                  # MarketMakingSPXCallSpreadProjectManager
├── data/
│   ├── data_loader.py                  # DataLoader(BaseDataLoader) — adds get_option_chain_data
│   ├── factor_manager.py               # FactorManager — SPX-specific factor pipeline
│   └── factor_normalizer.py            # Re-export only — points to misbuffet canonical version
├── models/
│   ├── model_trainer.py                # ModelTrainer — GBM model training pipeline
│   ├── pricing_model.py                # Black-Scholes + Greeks
│   └── volatility_model.py             # IV surface construction and forecasting
├── strategy/
│   ├── market_making_strategy.py       # Strategy — market regime detection, spread generation
│   └── risk_manager.py                 # RiskManager — delta/gamma/vega limits, VaR
├── backtesting/
│   ├── backtest_runner.py              # BacktestRunner(BaseBacktestRunner)
│   └── base_project_algorithm.py       # Algorithm(BaseProjectAlgorithm)
└── utils/
    ├── performance_metrics.py          # Standalone performance helpers
    └── validators.py                   # Data validation utilities
```

---

## Inheritance from misbuffet

All three core backtesting classes extend misbuffet base classes.  Only project-specific
logic lives in this folder; generic infrastructure is inherited.

### `BacktestRunner(BaseBacktestRunner)`
**File:** `backtesting/backtest_runner.py`

Implements the two abstract hooks:
```python
def setup_components(self, config) -> bool:
    # Creates ModelTrainer and Strategy for this project

def create_algorithm_instance(self) -> Algorithm:
    # Creates Algorithm(), injects trainer/entity_service/strategy
```

All generic methods are inherited: `run_backtest`, `run_backtest_async`,
`get_backtest_status`, `get_backtest_results`, `stop_backtest`, `_calculate_performance_metrics`.

Also contains mock simulation helpers for development: `_execute_backtest_simulation`,
`_simulate_trading_day`, `train_models`.

### `Algorithm(BaseProjectAlgorithm)`
**File:** `backtesting/base_project_algorithm.py`

Implements SPX-specific lifecycle:
```python
def initialize(self):
    super().initialize()           # sets lookback_window, train_window, models
    self.config = get_config()     # load SPX config
    # register SPX portfolio with EntityService
    # set universe, bar_size_setting, duration_str

def on_data(self, data):
    # run model trainer pipeline
    # set holdings via UnifiedPortfolioManager
    # update portfolio value and performance tracking
```

All reusable helpers are inherited: `_update_portfolio_value`, `_update_performance_tracking`,
`_log_daily_summary`, `_is_end_of_day`, `get_algorithm_state`, `set_entity_service`,
`set_factor_manager`, `set_trainer`, `set_strategy`.

SPX-specific helpers remain here: `_verify_and_import_data`, `_generate_new_opportunities`,
`_evaluate_and_execute_opportunities`, `_execute_spread_trade`, `_calculate_position_value`.

### `DataLoader(BaseDataLoader)`
**File:** `data/data_loader.py`

The full service chain (EntityService → MarketDataService → MarketDataHistoryService →
FactorService) is wired entirely in `BaseDataLoader.__init__`.  `DataLoader` only adds:

```python
def get_option_chain_data(self, expiration_dates, strike_range) -> Dict:
    # SPX-specific option chain fetching (IBKR integration pending)
```

### `factor_normalizer.py`
**File:** `data/factor_normalizer.py`

Re-export only — all normalization logic lives in misbuffet:
```python
from src.application.services.misbuffet.data.factor_normalizer import (
    FactorNormalizer, NormalizationMethod, NormalizationScope, NormalizationConfig,
)
```

---

## Pipeline flow

```
BaseProjectManager.run()
  └─ _run_backtest_stage()
       └─ BacktestRunner(database_service).run_backtest(config)
            ├─ setup_components(config)         # ModelTrainer + Strategy
            ├─ create_algorithm_instance()      # Algorithm + inject deps
            └─ Misbuffet engine → Algorithm.initialize() → Algorithm.on_data(bar)
```

---

## Configuration

Key fields in `DEFAULT_CONFIG` / `get_config()`:
```python
{
    'underlying_symbol': 'SPX',
    'underlying_exchange': 'CBOE',
    'spread_type': 'bull_call_spread',
    'default_dte_range': (7, 45),
    'default_delta_range': (0.15, 0.45),
    'max_spread_width': 50,
    'max_position_size': 10,
    'max_daily_loss': 5000,
    'historical_data_duration': '6 M',
    'bar_size_setting': '5 mins',
}
```

---

## Adding a second project

See `base_project/CLAUDE.md` for the template checklist and
`src/application/services/misbuffet/CLAUDE.md` for base class documentation.
