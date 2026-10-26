# Configurable strategy projects: audit and proposed architecture

Phase 1 deliverable (2026-10-26) for the task "Implement Configurable Investment Strategy Projects Through the
Flask Web Application". Part 1 is the audit of the three projects named by the task, part 2 the architecture
proposed for review before any code is written.

Projects audited (none is modified, renamed or merged):

| key | folder | manager class |
|---|---|---|
| `cross_sectional` | `project_managers/cross_sectionnal_project` | `CrossSectionalMomentumProjectManager` |
| `stm_reference` | `project_managers/spatio_temporal_momentum_project` | `SpatioTemporalMomentumProjectManager` |
| `stm_paper` | `project_managers/spatio_temporal_momentum_project_full` | `SpatioTemporalMomentumFullProjectManager` |

Two more projects exist and follow the same patterns at 10-minute bars: `spatio_temporal_momentum_project_10m`
and `cross_sectionnal_project_10m`. They are out of the task's scope but the registry below can take them as
two more adapters.

---

## Part 1 — Audit

### 1.1 What really differs

* **`stm_reference` and `stm_paper` are the same strategy and the same code.** Every file except `config.py`
  differs only in import paths and class names. `config.py` differs in: universe (2 random stocks per S&P
  sector with seed 42 vs the paper's 48 US financials), names (signal factor, model prefix, portfolio, results
  and weights folders) and the backtest start (2026-06-01 vs 2026-09-14, a 2-week smoke run). They are one
  strategy type with two universe definitions.
* **`cross_sectional` is a different strategy**: a per-asset LightGBM *classifier* with Optuna feature and
  hyper-parameter selection, quantile long/short book. STM is a joint-universe *neural network* trained to
  maximise the Sharpe ratio of its own positions, vol-scaled signal book.

### 1.2 Capability matrix

| | `cross_sectional` | `stm_reference` / `stm_paper` |
|---|---|---|
| **Universe** | explicit list: the paper's 46 US financials, delisted names replaced, merged names replaced (CADE→HWC, SNV→SSB, PNFP→FHN), HBAN added: 48 | `stm_reference`: random `n_per_sector` (2) per sector from `SECTOR_CONSTITUENTS`, seed 42. `stm_paper`: the paper list (still has PNFP) |
| Universe persistence | `Universe` + `UniverseConstituent` (point-in-time table), all constituents start at `price_history_start`, never ended | same |
| Eligibility at a decision | active constituent + has every feature of the model at the session | active constituent + close at the session + enough history rows |
| **Features** | 48 candidate domain factors (24 momentum + turnover, volume trend, price range, return extremes, return vs SPY, delta bands from IBKR implied vol and IRX), each computed by its own factor's `calculate()`; Optuna picks the subset; optional cross-sectional ranks | 7 engineered features: vol-normalised returns over (1, 5, 10, 21) sessions + 3 MACD signals ((2,6),(4,12),(8,24)), winsorised; windows configurable |
| Feature persistence | **none** (only the signal is stored) | features and signals stored as factor values (`STMFeatureStore`) |
| **Model** | LightGBM binary classifier | `SpatioTemporalMomentumNet` around reference models `lstm`, `slp`, `mlp`, `conv`, `tft` (TFT used); all assets in one network |
| Output contract | P(next-session return > cross-sectional median), per asset, in [0, 1] | position signal per asset (reference: tanh range [-1, 1]) |
| Objective | AUC (or top-minus-bottom Sharpe) on purged walk-forward folds | negative Sharpe of captured vol-scaled returns (`sharpe_loss`), optional L1 / turnover regularisers |
| Label / horizon | next session above the median (horizon configurable) | next-session vol-scaled return (prediction horizon 1) |
| **Training window** | rolling 252 sessions | rolling 84 sessions (expanding supported when `rolling_window_rows` is None) |
| Validation | 3 purged walk-forward folds inside the window | the latest 14 sessions (`val_days`), early stopping (10 epochs), purge 1 day |
| Hyper-parameter search | Optuna TPE, 40 trials, 600 s timeout; search space of 8 LightGBM parameters + feature subset | none (fixed parameters) |
| Retraining | every 21 calendar days | every 30 days, or when a model's assets are no longer all eligible |
| Model used from | the session it was trained (labels known at the session only) | the next session (`validation_end < session`) |
| Artifact compatibility | ML model name (prefix + type + universe name) + `model_hash` (whole config incl. universe tickers) + file present | ML model name + `model_hash` (features, model, horizon, scaling; not the universe) + stored asset list |
| **Decision / rebalance / execution** | one clock: daily at 16:00 using the previous session's close; rebalance = execution = decision | same |
| **Portfolio construction** | long top 20 % / short bottom 20 % of probabilities, inverse-vol weights inside each side, dollar-neutral, gross 1.0 (`long_short_weights`) | `w = signal × target_vol / (ann_vol × N)`, gross capped at 1.0 (`signals_to_weights`); net exposure unconstrained |
| Long-only / long-short | long-short only | long-short only (sign of the signal) |
| Orders | `UnifiedPortfolioManager.set_holdings` (market orders at the bar's price, backtest fills) | same |
| Costs | report only: bps × turnover scenarios | same |
| **Data** | daily TRADES, implied vol, SPY, IRX; preloaded before the run (`BacktestDataPreloadService`) | daily TRADES; no preload |
| Reports | `/csm` dashboard: performance vs equal-weight and 20d momentum L/S, quintiles, AUC, feature importance, Optuna history, coverage, PDF | `/stm` dashboard: performance, costs, coverage, PDF |
| Tests | `tests/cross_sectional_momentum` | `tests/spatio_temporal_momentum` (12 files) |

### 1.3 Limitations and risks found

1. **Configuration does not reach the algorithm.** Every project's `Algorithm.initialize()` calls its module's
   `get_config()`; a config passed to the project manager reaches the trainer but not the algorithm (portfolio
   name, results dir, universe). Runs with other parameters today require patching `DEFAULT_CONFIG` in memory.
   This must change before any web-configured run is trustworthy.
2. **Survivorship bias in every universe.** The constituent lists are today's lists (replacements chosen in 2026)
   projected back to the history start; `stm_reference` samples from current S&P sector lists. The
   point-in-time table exists but is filled with one start date and no end dates.
3. **Universe drift is silent.** Universes are get-or-create by name; constituents are never ended when the list
   changes, so the database keeps CADE / SNV / PNFP as active members of the paper universe.
4. **No experiment record.** A run is identified by its results folder (overwritten by the next run) and its
   artifacts; nothing links a report to the exact configuration, universe membership, data coverage and models
   used.
5. **Cross-sectional features are not stored** (option C of 2026-10-26): a decision cannot be audited from the
   database. STM already stores them.
6. **`MLModel.configuration` is written once** (get-or-create by name) and goes stale when the configuration
   changes; the artifact metadata is the real record.
7. **The engine's own summary is wrong** ($1,000,000 / 0 trades: it reads the legacy portfolio and a hardcoded
   0); the project reports are the reliable numbers.
8. **Duplicated code**: STM reference / paper are copies; `price_ingestion`, `universe_setup`, `backtest_runner`
   and the algorithms are near-identical across all projects.
9. **Single clock**: signal, rebalance and execution cannot differ; there is no "do not trade if the signal has
   not changed materially" rule.

### 1.4 What can be shared without changing any methodology

* Configuration records, versioning, validation framework, job execution, experiment records, comparison.
* Universe snapshot recording (which constituents were active and eligible at each decision).
* Feature/signal persistence (STM's store pattern, extended to the cross-sectional features).
* Evaluation: `strategy_metrics`, cost scenarios, data coverage, report store.

Not shared: feature construction, models, training loops, artifact formats and the two portfolio rules. They are
wrapped, not merged.

---

## Part 2 — Proposed architecture

### 2.1 Layers

```
domain/entities/strategy/            pure: StrategyConfiguration, ConfigurationSection, ConfigurationStatus,
                                     StrategyExperiment, ExperimentKind/Status, ProjectCapabilities,
                                     OutputContract, PortfolioRule (+ validation rules, no I/O)
domain/ports/strategy/               StrategyConfigurationPort, StrategyExperimentPort
application/services/strategy/       ProjectRegistry + one adapter per project, StrategyConfigurationService,
                                     ExperimentService, JobRunner (subprocess worker), ComparisonService
infrastructure/models/strategy/      strategy_configurations, strategy_experiments (JSON payload columns)
infrastructure/repositories/...      local repositories + mappers
interfaces/flask/web/controllers/    strategy_controller.py (/strategies), templates; no repository access
```

### 2.2 Strategy configuration (versioned, immutable once used)

* One record per *version*: `name`, `description`, `project_key`, `version`, `parent_id`, `status`
  (`draft` → `validated` → `locked`; `archived`), `content_hash`, `created_at`, and the sections `universe`,
  `factors`, `model`, `training`, `portfolio`, `trading`, `risk`, `evaluation`, `data_policy` stored as JSON
  validated by the project's schema.
* A configuration is **locked** as soon as an experiment starts on it; editing a locked configuration creates a
  new version (`parent_id` = the old one). The content hash detects identical clones.
* Reuses existing entities rather than duplicating them: `Universe` / `UniverseConstituent` (selected universe and
  point-in-time membership), `Factor` (registered factors), `MLModel` / `ModelTraining` / `ModelArtifact` /
  `TrainingMetric` (training provenance). Only two new tables: configurations and experiments.

### 2.3 Project registry and capabilities

Each project gets a thin adapter (`ProjectAdapter`) registered by key; nothing branches on folder names.

```python
class ProjectAdapter(Protocol):
    key: str                                   # 'cross_sectional', 'stm_reference', 'stm_paper'
    def capabilities(self) -> ProjectCapabilities: ...      # supported models, output contract, portfolio
                                                             # rules, frequencies, universe modes, lifecycle ops
    def schema(self) -> dict: ...                            # per section: field, type, bounds, choices, help
    def default_configuration(self) -> dict: ...             # = today's DEFAULT_CONFIG, so defaults reproduce it
    def validate(self, configuration) -> list[ValidationIssue]: ...
    def native_config(self, configuration) -> dict: ...      # the project's own config dict, nothing else
    def run_backtest(self, native_config, progress) -> ExperimentResult: ...   # calls the existing manager
```

The adapter translates a configuration into the dict the existing manager already understands; the manager, its
cycle, model and portfolio rule run unchanged. Defaults reproduce today's `DEFAULT_CONFIG` exactly (regression
tests assert it).

What each adapter can expose honestly today:

| section | `cross_sectional` | `stm_*` |
|---|---|---|
| universe | registered universe or explicit tickers | registered universe, explicit tickers, or sector sample (n, seed) |
| factors | include / exclude among the 48 candidates, cross-sectional ranks | return horizons, vol lookback, MACD pairs, winsorisation |
| model | LightGBM: Optuna search bounds, trials, folds, metric (`auc`, `long_short_sharpe`), seed | type (`tft` tested; others only if tests pass), lookback, encoder length, architecture params |
| training | rolling window, retrain every N days, label horizon | rolling or expanding, val days, epochs, early stopping, lr, batch, regularisers, retrain every N days |
| portfolio | quantile, gross exposure (method fixed: quantile L/S inverse-vol) | target vol, gross cap (method fixed: vol-scaled signal) |
| trading / evaluation | backtest dates, capital, cost scenarios (bps) | same |

Everything else in the task list (long-only, top-N, max weight, net exposure, borrow constraints, turnover limits,
separate rebalance/execution frequencies, order types, slippage model, benchmark choice, regression targets) is
**listed as unsupported** by the capabilities and rejected by validation until implemented and tested. A later
phase can add portfolio rules as pure functions validated against the output contract (e.g. a probability output
cannot feed a rule that needs expected returns).

### 2.4 Experiments and jobs

* `StrategyExperiment`: configuration id + content hash, kind (`backtest`; `training` alone is not possible today:
  both projects train inside the engine as time advances), status (`queued`, `running`, `succeeded`, `failed`,
  `interrupted`), job pid / host / heartbeat, log path, results dir (one per experiment, never overwritten), and
  links to what the run used: artifacts (`ModelArtifact` ids), universe snapshot (active and eligible members per
  decision), preload coverage report, report summary metrics.
* `JobRunner` starts a **separate worker process** (`python -m src.application.services.strategy.worker <id>`),
  not a thread inside Flask: a run takes hours, uses IBKR and SQL Server, and must survive a web restart. The
  worker writes status + heartbeat to the experiment row and also through the existing `JobRecorder` (so the
  monitoring dashboard sees it). On web start, a `running` experiment whose process is gone becomes `interrupted`.
* One run at a time per IBKR client id; a second launch is queued or refused.
* **No live trading** from this interface: experiments are backtests. Paper/live stay out of scope until asked,
  and would need their own explicit confirmation step.

### 2.5 Option C: every decision's inputs stored

For the cross-sectional project, a `CSMFeatureStore` mirrors `STMFeatureStore`: one feature factor per candidate
(registered once, no values until used) and, per decision, the values of the features the model scored, as
factor values dated at the decision. Controlled by `data_policy.persist_features` (`decisions` default for daily,
`off` default for 10-minute bars because of volume). Together with the signal, the artifact id and the universe
snapshot, a decision becomes fully reproducible from the database.

### 2.6 Flask (`/strategies`)

Dashboard (configurations, versions, experiments), create/edit wizard whose forms are rendered from the adapter
schema (only supported fields appear), server-side validation, preview (JSON + diff vs parent), save, clone,
launch backtest (returns immediately), job page (status, log tail, progress), artifacts, comparison, and links to
the existing `/csm` / `/stm` result pages of the experiment. Routes call application services only.

### 2.7 Comparison

Compares experiments only on their out-of-sample decisions, shows period / universe / cost assumptions side by
side and flags pairs that are not comparable (different periods or universes). Never ranks on in-sample Sharpe.

### 2.8 Phases

1. Domain + persistence + registry with the three adapters; fix (1.3-1) so the manager's config reaches the
   algorithm; regression tests proving defaults reproduce today's runs.
2. Experiments, worker process, recovery; option C store; universe snapshot recording.
3. Flask `/strategies` workflow.
4. Comparison, report links, remaining tests.

### 2.9 Owner decisions (2026-10-26)

1. The two tables are created in `base_infra` (on connection, `create_all`): approved.
2. Experiments run in a separate worker process: approved.
3. Constituents that leave a universe list are ended from the day of the change: approved.

---

## Part 3 — Implementation status (2026-10-26)

### Where things are

| Layer | Files |
|---|---|
| Domain | `domain/entities/strategy/` (`strategy_configuration.py`, `configuration_schema.py`, `project_capabilities.py`, `strategy_experiment.py`), `domain/ports/strategy/strategy_ports.py` |
| Infrastructure | `infrastructure/models/strategy/`, `infrastructure/repositories/{local_repo,mappers}/strategy/`, `FactorValueRepository.add_bulk` |
| Application | `application/services/strategy/` (`project_adapters.py` = registry + 3 adapters, `configuration_service.py`, `experiment_service.py`, `experiment_worker.py`, `strategy_services.py`); `cross_sectional_momentum/csm_feature_store.py` (option C) |
| Interfaces | `interfaces/flask/web/controllers/strategy_controller.py` (`/strategies`), `templates/strategies_*.html` |
| Tests | `tests/strategy/` (configuration, experiments, web), `tests/cross_sectional_momentum/test_csm_feature_store.py` |

### Changes to existing code (behaviour-preserving, regression-tested)

* The three projects' runners hand their config to the algorithm (`project_config`); without one the algorithm
  still uses `get_config()`.
* `STMUniverseService.ensure_universe` ends members that left the list and re-admits returning ones.
* `CSMSignalStore` dates signals by bar (`bar_key`): daily unchanged; the 10-minute project kept only the first
  decision of each day before.
* `CSMConfiguration.persist_features` (default False; the daily project sets True), excluded from the model hash.

### Implemented

Versioned configurations (draft / validated / locked / archived, revise, clone, content hash), schema-driven
validation per project, the three adapters (defaults reproduce `DEFAULT_CONFIG` exactly), backtest experiments in
a worker process (heartbeat, recovery, one run at a time, own results folder and portfolio), provenance (artifacts,
universe membership per decision, preload report), headline metrics, the project's own report per experiment,
artifact inspection, comparison with comparability warnings, the `/strategies` web workflow, option C.

### Not yet supported (explicitly declared by each adapter)

Long-only / long-and-cash / top-N, weight / net / turnover / borrow limits, separate signal / rebalance / execution
frequencies, order types and slippage models, benchmark choice, training without a backtest, STM model types other
than TFT end to end, paper and live trading. The 10-minute projects are not registered yet (two more adapters).
