# CLAUDE.md – backtest_registry (generic research / backtest registry, 2026-11-18)

**Models are reusable research artifacts. Runs are executions. Universes belong to runs, not to models.**

```
              MODEL REGISTRY (existing ML registry: ml_models, model_features, model_trainings,
                    |          model_artifacts, training_metrics - nothing new for models)
                    | backtest_run_models (run <-> model, role 'A (traded)', 'B', artifact)
                    v
              BACKTEST RUN (backtest_runs: identity, config snapshot, commit, window, progress, assumptions, status)
             /                      \
   MISBUFFET ENGINE                  RESEARCH RESULTS
   backtest_run_portfolios ->        research_series (named dated series: 'A/gross/D10-D1', 'unused_premium')
   portfolios / orders / positions   run_metrics (scope 'engine' from the value curve; project scopes 'A/gross' ...)
   / daily PortfolioValueFactor
```

## Lifecycle (BaseBacktestRunner, every project, automatic)

`BaseBacktestRunner.run_backtest` (`src/application/services/misbuffet/engine/base_backtest_runner.py`):

1. `_register_run`: `BacktestRunService.register` stores the FULL config (`run_manifest._jsonable`, secrets
   redacted), its sha256, the git commit / branch / dirty flag, the requested window, `months_planned`, and what the
   project's `describe_run(config)` adds (universe description + snapshot with `point_in_time_membership`,
   price source, dividends, transaction costs, gross leverage, assumptions). Status PENDING -> RUNNING.
2. **Own book**: `config['Portfolio']['name']` becomes `<name>_run<id>` (on a copy of the config). Backtests used to
   `_replace_or_create` the same portfolio every run, wiping the previous run's orders / positions / values; now every
   run keeps its book. Turn off with `run_registry: {'unique_portfolios': False}`.
3. `_track_bars` wraps the algorithm's `on_data`: every processed bar moves `actual_start / actual_end`,
   `bars_processed`, `months_completed` and the heartbeat (written at most every 30 s).
4. `_finish_run`: registers the main portfolio and its sub-portfolios (holdings tree), links the ML models of the
   artifacts the run used (`run_manifest.models_of`), decides the status, computes the engine metrics.

**Status is decided from what was processed** (`BacktestRun.finish`): COMPLETED only when the last processed bar is
within 4 days of the requested end. An engine that returns early is PARTIAL (`"23 / 69 months"`), an exception is
PARTIAL if months were processed else FAILED, Ctrl-C is CANCELLED. `BacktestRunService.recover()` closes RUNNING runs
whose worker is gone (no heartbeat for 10 min and the pid is dead).

A registry failure (database unreachable, tables missing) is logged and never stops a backtest;
`run_registry: {'enabled': False}` turns it off.

## Publishing research results (projects)

```python
run, service = self.runner.run, self.runner._registry_service          # after / during run_backtest
results = ResearchResultService(service.factory)
results.publish_frame(run.id, frame, group="A/gross", prefix="A/gross/")  # any named series
results.publish_metrics(run.id, {"D10-D1.sharpe_ratio": 0.8}, scope="A/gross")
ModelRegistryService(service.factory).register_model(name, algorithm, configuration={features, hyperparameters,
                                                      training_frequency, prediction_frequency, version})
service.link_model(run, model.id, role="A (traded)")
```

Republishing replaces the run's points of the same series names (publish after every month: a PARTIAL run keeps the
months it completed). Done by `stm_monthly_decile_project` (`decile_report.publish_research`, models A / B) and
`etf_dispersion_stm_project` (`dispersion_report.publish_research`).

## Reading (web)

`ResearchQueryService` (runs with filters and headline metrics, detail, daily downsampled equity, series, metrics,
models, `compare`). `compare` uses the pure domain module `src/domain/entities/backtest/run_comparison.py`: field
differences, flattened config-snapshot differences and warnings (universes, price sources, dividends, costs, windows,
capital, leverage, membership rules, PARTIAL / not-completed runs, uncommitted code). **Viewable is not comparable**:
nothing is refused, everything that differs is said.

- API `src/interfaces/flask/api/controllers/research_controller.py`: `/api/backtests`, `/api/backtests/<id>`
  (`/equity`, `/metrics`, `/series`), `/api/backtests/compare?run_ids=`, `/api/models`, `/api/models/<id>`
  (`/runs`, `/artifacts`).
- Pages `/research/` (runs), `/research/runs/<id>`, `/research/compare?run_ids=`, `/research/models`,
  `/research/models/<id>`; also standalone: `python -m src.interfaces.flask.research_app` (127.0.0.1:8053).
- Read only: `read_access.py` builds the session on the monitor's guarded engine (`guard_read_only`; the Docker
  read-only login when `DB_READONLY_USER` is set). Never `DatabaseService` (it creates missing tables).
- Backtests never run in the web process: launch from `/strategies` (ExperimentService -> worker process; the run
  links back through `strategy_experiment_id`) or as their own process (`python -m <project manager>`).

## Reproducibility

Commit + dirty flag + full config + universe snapshot + price source say how a result was produced. They do not pin
the market data: `factor_values` can change (a re-imported or extended series). `data_snapshot` records the database
name and the changed files of a dirty tree; a project can add its data coverage there (`describe_run`).

## Tables (created 2026-11-18 on base_infra_test; base_infra needs the owner's approval + COPY_ONLY backup)

`backtest_runs`, `backtest_run_portfolios` (unique portfolio_id: one portfolio -> one run), `backtest_run_models`,
`research_series` (index run_id, series_name, date), `run_metrics` (unique run_id, scope, metric_name).
NOTE: `BaseFactory` runs `create_all` whenever a project starts, so the first project run on a database creates them.

The older `models` / `backtests` tables (`src/domain/entities/backtest/model.py`, `backtest.py`) are empty and have no
writer; this registry supersedes them (not removed).

Tests: `tests/backtest_registry/test_backtest_registry.py`; project publishing in `tests/stm_monthly_deciles` and
`tests/dispersion`.
