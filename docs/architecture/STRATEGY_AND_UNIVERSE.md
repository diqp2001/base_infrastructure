# Strategy and Universe domain models (2026-11-19)

A strategy and the universe it uses are persistent domain concepts, so the large project configuration
dictionary is no longer their only definition.

```
Strategy (strategies)                         what the strategy IS, one row per version
  | universe_id
  v
Universe (universes, universe_type)           a reusable LISTING of constituents: no weight, no rank, no allocation
  |-- UniverseFinancialAsset (universe_financial_assets)  -> FinancialAsset (financial_assets)
  |                                                         optional start_date / end_date (end exclusive)
  |-- UniverseFactor (universe_factors)                   -> Factor (factors)
  '-- child type InvestmentUniverse (investment_universes, id = universes.id)
        entity_type, currency_id; its dated / weighted history: UniverseConstituent (universe_constituents)
```

## Owner's decisions

These decisions were made on 2026-11-19.

- **Universe and its children.** `universes` is the parent table, and `investment_universes` (the 49 universes the
  projects use) is a child type of it. The child uses joined-table inheritance with the same id, so its
  `universe_constituents` and the model trainings keep their foreign keys. The former backtest `Universe` was an
  empty table used only by tests and the entity upload; it is replaced.
- **Dated membership.** `UniverseFinancialAsset` has optional `start_date` / `end_date`, and `UniverseFactor` has
  no dates.
- **Strategy replaces StrategyConfiguration.** The versions, the draft → validated → locked → archived lifecycle,
  the content hash and the project sections are unchanged. Former names still import as aliases:
  `StrategyConfiguration`, `StrategyConfigurationService`, `StrategyConfigurationRepository`,
  `configuration_id` / `project_key` on entities, and `strategy_configuration_local_repo`.

## Storage: strategies, parameters, parameter values (2026-11-19)

| table | one row per | columns |
|---|---|---|
| `strategies` | strategy version | id, name, version, parent_id, strategy_type, description, status, content_hash, universe_id (FK), created / validated / locked |
| `strategy_parameters` | distinct parameter | id, section, name (unique together), description |
| `strategy_parameter_values` | (strategy, parameter) | strategy_id, parameter_id (unique together), value (text), value_type (null / bool / int / float / str / json), value_numeric (int / float copy, for filtering) |

- **Every parameter is a row.** That includes the shared typed fields: section `definition`, names `bar_frequency`,
  `bar_size`, `model_type`, `training_window`, `retrain_every_days`, `prediction_horizon`.
- **Nested sections.** A parameter's name is its path in the section, JSON-pointer style, for example section
  `model`, name `stm.model/params/hidden_dim`. A list is one value (JSON). Empty settings and empty sections keep a
  row, so a strategy rebuilds exactly and its content hash does not change.
- **Codec.** `src/infrastructure/repositories/mappers/strategy/strategy_parameter_codec.py`.
- **Repository.** `StrategyRepository` writes the rows when it saves a strategy, replacing the previous ones, and
  rebuilds the strategy when it reads (one query for a whole list). `parameter_values(section, name)` gives one
  parameter across strategies.

Example, the strategies whose training window exceeds 200:

```sql
SELECT s.name, s.version, v.value
FROM strategies s
JOIN strategy_parameter_values v ON v.strategy_id = s.id
JOIN strategy_parameters p ON p.id = v.parameter_id
WHERE p.section = 'definition' AND p.name = 'training_window' AND v.value_numeric > 200;
```

## Strategy: what is a column, what stays in sections, what is not a strategy

| kind | fields |
|---|---|
| identity | id, name, version, parent_id, status, content_hash, created / validated / locked timestamps |
| identity columns + typed definition (parameter rows, section `definition`) | `strategy_type` (ProjectRegistry key), `universe_id` (columns); `bar_frequency`, `bar_size`, `model_type`, `training_window`, `retrain_every_days`, `prediction_horizon` |
| project parameters (`sections`, stored as parameter rows; validated by the project's schema when it has one) | `parameters` = model, training, trading, evaluation and data_policy; `features` = factors; `portfolio_construction` = portfolio; `risk` |
| **not** a strategy (future `StrategyDeployment`) | the `live` block: account, host, port, client_id, paper_bar_prices, allow_delayed_prices, max_quote_age_seconds, order windows, supervisor, plus results / weights folders |

The typed definition is read from the project's native config (`project_adapters.strategy_definition`) when a strategy
is created and each time it is validated:

- `bar_size_setting` gives `bar_size`;
- `stm.bar_minutes` or the bar size gives `bar_frequency`;
- `model_type` or `stm.model.model_type` gives `model_type`;
- `training_window` or `stm.training.rolling_window_rows` gives `training_window`;
- `retrain_every_days` gives `retrain_every_days`;
- `prediction_horizon` or `stm.prediction_horizon` gives `prediction_horizon`.

The `content_hash` covers the type, the typed definition, the universe and the sections. Without typed fields it
equals the former configuration hash, so migrated experiments still match their strategy.

## Rules

- **Universe membership is a set.** A financial asset cannot hold two overlapping memberships in the same universe,
  and a factor cannot be listed twice. The `Universe` entity raises `DuplicateMembership`, and so do the membership
  repositories.
- **Database constraints:**
  - `UNIQUE(universe_id, financial_asset_id, start_date)`;
  - `UNIQUE(universe_id, factor_id)`;
  - `UNIQUE(name, version)` on both `universes` and `strategies`.
- **Holding weights.** Weights, ranks, scores and allocations belong to portfolio construction or model output.
  An ETF's holding weights are the ETF's composition and stay in `universe_constituents.weight`, where the
  dispersion factors read them.
- **A locked strategy never changes.** This includes its universe reference: to change it, create a revision.

## Code

| layer | files |
|---|---|
| domain | `src/domain/entities/strategy/strategy.py`, `.../universe/{universe, investment_universe, universe_financial_asset, universe_factor}.py` |
| ports | `src/domain/ports/strategy/strategy_ports.py`, `src/domain/ports/universe/universe_port.py` |
| ORM | `src/infrastructure/models/strategy/strategy.py`, `.../universe/{universe, universe_financial_asset, universe_factor}.py` |
| mappers | `.../mappers/strategy/strategy_mapper.py`, `.../mappers/universe/universe_mapper.py` |
| repositories | `.../local_repo/strategy/strategy_repositories.py`, `.../local_repo/universe/{universe_repository, investment_universe_repository, universe_membership_repositories}.py`; factory keys `Strategy`, `Universe`, `UniverseFinancialAsset`, `UniverseFactor`, `InvestmentUniverse` |
| service | `src/application/services/strategy/strategy_service.py` (`StrategyService.assign_universe`) |
| migration | `src/infrastructure/database/strategy_universe_migration.py` |
| tests | `tests/universe/`, `tests/strategy/test_strategy_entity.py` |

## Every project registers its Strategy when it runs

Each project under `src/application/managers/project_managers` registers its Strategy when it runs, through
`ProjectStrategyRegistrar` (`src/application/services/strategy/project_strategy_registration.py`):

| how the project runs | where it registers |
|---|---|
| `BaseBacktestRunner.run_backtest`: cross_sectional (+10m), etf_dispersion_stm, market_making_SPX (+v2, and `base_project`, its template), stm (+10m, 10m_hourly, full), stm_monthly_deciles | `_ensure_strategy` before the run is registered; `_sync_strategy_universe` after setup and at the end |
| `LiveRunner.run_live` (stm 10m_live) | the same hooks |
| `MarketMakingBacktestRunner.run_backtest` (market_making_project), test_base_project `BacktestRunner.run_backtest` | `register_with_database` at the start, sync at the end |
| etf_dispersion_screener_project `run` | `_register_strategy`. It opens the database when the screener has none. Its sections are the screen's parameters. Its instruments are listed only when ETF tickers are given explicitly, because the screened list changes every day. |

How a registration works:

- **Name and type.** Both are the project folder. The folder is unique, whereas two projects share the
  `project_name` 'market_making_spx_call_spread'.
- **Sections.** They hold the config's strategy parameters, grouped. The run settings are excluded (backtest window,
  capital, results folder, run name, the Portfolio's name and cash) and so is the deployment (`live`, supervisor,
  web, MLflow, data folders, `ibkr`). Credentials are redacted.
- **Typed definition.** It comes from `strategy_definition(config)`.
- **Universe.** Each version gets a Universe named '<folder> universe'. Its members are the config's `universe`
  instruments that are stored as financial assets. The symbol and asset type are matched, ignoring case and
  underscores. Instruments the run creates are added at the end.
- **Versions.** A config whose definition is unchanged reuses its version, so a re-run with another window or
  capital is the same strategy. A changed config gets a new version, with parent = the latest. A new Universe
  version is created only when the instruments change. Registered versions are locked, because they are what a run
  used.
- **Runs launched from /strategies.** Their config carries `strategy_experiment_id`, so they keep their own strategy
  and only its universe is synchronised.
- **Failures.** A registration failure is only logged and never fails a run. `register_strategy: False` in a config
  turns registration off.
- **Display.** On /strategies, these strategies are shown read-only. They have no web project adapter: to edit one
  as a schema, create a strategy of an adapter type.

Tests: `tests/strategy/test_project_strategy_registration.py` (every project folder is wired; every default config
gives a valid strategy without run or deployment settings).

## Designing and running a strategy (/strategies)

### Pages

- **Dashboard.** It lists every strategy version with its trading bar, model, training window, retraining,
  horizon, universe size and factor count.
- **"Create a new strategy from this one".** On any strategy, it creates a draft with its own copy of the universe
  (`StrategyDesignService.derive`).
- **Design page** (`/strategies/<id>/design`, drafts only). Each part saves separately:
  - trading, model and training: the model dropdown, the decision interval in minutes, the data bar, the training
    window, retraining and horizon;
  - the financial-asset universe: one line per type, e.g. `CompanyShare: JPM, BAC`;
  - the factor universe: a checklist of the stored factors;
  - the parameter sections (JSON).
- **Strategy types with a web form** (`stm_reference`, `stm_paper`, `cross_sectional`). Their model, windows and
  constituents are edited in their project form.
- **Copy-on-write.** A universe that other strategies also use is copied before it changes.

### Running

`ProjectRegistry.get(<project folder>)` returns a `ProjectFolderAdapter`. A project strategy is launched like a
web-configured one: validate it, then "Launch backtest". `strategy_project_config.apply_strategy` writes the
strategy onto the project's own `get_config()` (deep copy):

- **Sections.** Every stored key goes back to its place. `stm.<x>` goes into the stm section, and JSON lists and
  class keys get the project's shapes back. The project's own factor class definitions are kept.
- **Universe.** `config['universe']` becomes the strategy's instruments, in the order listed, which is the model's
  asset order. For STM projects the explicit ticker list is set, and the universe gets a name of its own
  (`<name>__strategy<id>`).
- **Typed fields.**
  - `bar_size` sets `bar_size_setting`.
  - `bar_frequency` sets `stm.bar_minutes` (the data bars). The decision interval is
    `trading.config_interval.custom_interval_minutes`.
  - The model is applied as described under "Models".
  - `training_window` is written only where the config has that key. `stm.training.rolling_window_rows` follows it
    only where the project uses one number for both.
  - `retrain_every_days` and `prediction_horizon` are written as is.
- **Run settings.** The backtest window, capital, `live` block and folders stay the project's. Each experiment gets
  its own results folder and portfolio.

The worker runs the project's manager (`manager_class()(config=..., database_service=...)`). A project without a
report object succeeds with its scalar results (`results_summary`). Applying the strategy registered from a config
gives that config back (tested for every project).

Launchable projects are those whose manager takes `config` and `database_service`, excluding the live STM project
and the screener (`NOT_LAUNCHABLE`): cross_sectional (+10m), etf_dispersion_stm, SPX v2, stm (+10m, 10m_hourly,
full) and stm_monthly_deciles.

### Models (`model_catalog.py`)

| project | models offered |
|---|---|
| STM-based (config has `stm`) | `tft`, `conv` (temporal convolution), `lstm`, `mlp`, `slp` (`stm_models.MODEL_MAPPING`) |
| cross-sectional momentum (`csm`) | `lightgbm` |
| others | the model their config names |

- **Parameters on a switch.** Switching model keeps only the parameters the new network's constructor accepts.
  For example, a TFT's `emb_dim` and `n_heads` never reach an LSTM, which takes `n_units` and `dropout`.
- **Encoder length.** It is checked only for the TFT.
- **Validation.** A model the project cannot train is refused when the strategy is validated.
- **Web forms.** The STM form offers all five networks.
- **Tests.** Every STM network goes through the Sharpe-loss walk-forward: it trains, stores its artifact, and the
  reloaded artifact reproduces the predictions (`tests/strategy/test_strategy_run_from_design.py`).

### Not wired yet

- **Factor universe.** It is stored, edited and shown, but the projects do not read it. Their features are their
  own configured factors. Feeding selected factors to a model as extra features is a per-project change.
- **Point-in-time membership.** stm_monthly_deciles and etf_dispersion_stm take their members from the
  point-in-time DJIA / DIA membership. The instruments list only sets which shares the engine can trade.

## Migrating an existing database

The migration rebuilds tables, so `BaseFactory._migrate_schema` never applies it; it only prints a warning while
the migration is pending. Run it explicitly:

```
python -m src.infrastructure.database.strategy_universe_migration            # dry run
python -m src.infrastructure.database.strategy_universe_migration --apply    # COPY_ONLY backup + verify, then migrate
```

The migration runs in one transaction and keeps every id:

- `universes` is rebuilt in the new shape;
- every `investment_universes` row gets its parent row;
- the child table is rebuilt without its own identity column;
- `strategy_configurations` are copied into `strategies`, with `project_key` becoming `strategy_type`;
- `strategy_experiments` is rebuilt with `strategy_id`, `strategy_hash` and `strategy_type`.

The foreign keys onto the rebuilt tables are dropped and restored: `universe_constituents`, `model_trainings` and
`backtest_runs`. `strategy_configurations` is left in place, unused. The migration was tested on SQLite and on
`base_infra_test` with data. Applying it to `base_infra` needs the owner's approval.

## Follow-up: code that should move to `Strategy.universe_id`

- **Inline universes in project configs.** Nine project configs define `'universe': {CompanyShare: [tickers]}`:
  cross_sectional (+10m), etf_dispersion_stm, stm (+10m, 10m_hourly, 10m_live, full) and stm_monthly_deciles. The
  algorithms read it as `self.config['universe']` to build holdings (`UnifiedPortfolioManager`), and so does SPX v2
  (options).
- **Universe setup per project.** `data/universe_setup.py` in every STM / CSM project, `STMUniverseBuilder`
  (`stm_universe.py`) and `IndexUniverseSetup` write `InvestmentUniverse` + `UniverseConstituent` rows by name.
  They could produce a Universe whose id a Strategy references.
- **Name lookups.** ML trainers and providers (lgbm momentum, implied vol), `misbuffet/algorithm/base.py`,
  `market_data_service.py` and `factor_research.py` look universes up by name.
- **Strategy sections.** A project's `universe` section (tickers, mode) still describes the universe. Once projects
  read `Strategy.universe_id`, that section should become a reference.
