# CLAUDE.md – base_project

## Purpose

`base_project` is a **lightweight project template** that demonstrates the minimal structure
needed for a Misbuffet-backed backtest pipeline.  It contains stubs for strategy, models,
and factor management but does **not** contain its own backtest runner or algorithm —
those are delegated to `market_making_SPX_call_spread_project` (concrete implementation)
and ultimately inherit from the reusable base classes in `misbuffet/`.

Use this package as a starting point when building a new project manager.

---

## Structure

```
base_project/
├── config.py                  # DEFAULT_CONFIG, get_config() — database and backtest settings
├── project_manager.py         # BaseProjectManager — thin orchestrator
├── strategy/
│   └── market_making_strategy.py   # Stub strategy
├── models/
│   └── model_trainer.py            # Stub model trainer
├── data/
│   └── factor_manager.py           # FactorManager — factor pipeline helpers
└── backtesting/
    └── __init__.py                 # Empty — runner and algorithm live in misbuffet / SPX project
```

---

## Key class: `BaseProjectManager`

`project_manager.py` wires together a minimal pipeline:

```python
class BaseProjectManager(ProjectManager):
    def __init__(self):
        self.database_service = DatabaseService(config.CONFIG_TEST['DB_TYPE'])
        self.backtest_runner = BacktestRunner(self.database_service)  # from SPX project
        ...

    def run(self, initial_capital, start_date, end_date, **kwargs) -> Dict:
        ...  # runs _run_backtest_stage(), _compile_final_results()
```

`BacktestRunner` is imported from:
```python
from src.application.managers.project_managers.market_making_SPX_call_spread_project.backtesting.backtest_runner import BacktestRunner
```

This is intentional — `base_project` has no concrete runner of its own; it borrows the
SPX project's `BacktestRunner(BaseBacktestRunner)` for demonstration purposes.

---

## `ModelTrainer` pattern

`models/model_trainer.py` shows the two-layer ModelTrainer pattern every project follows:

```
misbuffet/engine/base_model_trainer.py   ← generic factor layer (shared)
        │
        └── base_project/models/model_trainer.py   ← project shell
                │
                └── market_making_SPX_call_spread_project/models/model_trainer.py  ← full impl
```

**What `BaseModelTrainer` provides (do not duplicate in projects):**
- `__init__` — wires `BaseDataLoader`, `FactorManager`, `FactorNormalizer`
- `_ensure_factors_exist` / `create_factors` / `_create_factor_from_config` — factor creation from config
- `_create_price_dependencies_for_return_factor` — factor dependency wiring
- `_load_ticker_price_data` — generic price data retrieval
- `_prepare_factor_data` — the full factor pipeline: ensure factors → set frontier → build entities → batch fetch values

**What each project's `ModelTrainer` adds:**
```python
class ModelTrainer(BaseModelTrainer):
    def __init__(self, database_service):
        super().__init__(database_service, get_config(), get_trading_config())
        self.model = None          # assign the project's concrete ML model here
        self.tensor_splitter = None  # assign the project's tensor factory here

    def train_complete_pipeline(self, ...):   # project-specific step orchestration
    def _normalize_and_enhance_factors(self, ...):  # project normalisation strategy
    def _create_training_tensors(self, ...):  # project tensor format
    def _map_factor_names(self, ...):         # project feature name mapping
    def _train_models(self, ...):             # project model training loop
    def _evaluate_model_performance(self, ...): # project evaluation metrics
```

`base_project/models/model_trainer.py` provides empty stubs for all project-specific
steps so the class is instantiable.  Concrete projects (e.g. SPX) override every stub
with their real implementation.

---

## What is NOT here

| File | Why removed | Where it lives now |
|------|-------------|--------------------|
| `backtesting/backtest_runner.py` | Generic logic extracted to misbuffet | `misbuffet/engine/base_backtest_runner.py` |
| `backtesting/base_project_algorithm.py` | Generic lifecycle extracted to misbuffet | `misbuffet/algorithm/base_project_algorithm.py` |
| `data/data_loader.py` | Now a misbuffet responsibility | `misbuffet/data/base_data_loader.py` |
| `data/factor_normalizer.py` | Canonical version in misbuffet | `misbuffet/data/factor_normalizer.py` |

---

## Creating a new project from this template

1. Copy this folder to a new name under `project_managers/`.
2. Implement `BacktestRunner(BaseBacktestRunner)` with `setup_components` and
   `create_algorithm_instance` hooks.
3. Implement `Algorithm(BaseProjectAlgorithm)` with project-specific `initialize()` and
   `on_data()`.
4. Implement `DataLoader(BaseDataLoader)` if you need project-specific data fetching.
5. Update your `project_manager.py` to import your own concrete runner.

See `market_making_SPX_call_spread_project/` for a complete reference implementation.
See `src/application/services/misbuffet/CLAUDE.md` for documentation of the base classes.
