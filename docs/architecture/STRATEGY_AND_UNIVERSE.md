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

## Strategy: what is a column, what stays in sections, what is not a strategy

| kind | fields |
|---|---|
| identity | id, name, version, parent_id, status, content_hash, created / validated / locked timestamps |
| typed definition (columns) | `strategy_type` (ProjectRegistry key), `universe_id`, `bar_frequency`, `bar_size`, `model_type`, `training_window`, `retrain_every_days`, `prediction_horizon` |
| project parameters (JSON `sections`, validated by the project's schema) | `parameters` = model, training, trading, evaluation and data_policy; `features` = factors; `portfolio_construction` = portfolio; `risk` |
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
