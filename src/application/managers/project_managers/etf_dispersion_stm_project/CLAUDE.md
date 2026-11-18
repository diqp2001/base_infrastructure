# CLAUDE.md – etf_dispersion_stm_project

## Monthly, model-filtered ETF dispersion on DIA (created 2026-11-16; Misbuffet engine since 2026-11-16)

**The research question:** keep the original dispersion trade's short-ETF-call financing. Does the spatio-temporal
momentum (STM) model improve the trade if we skip long calls on constituents it does not expect to rise?

- **Strategy A (original):** short N ATM DIA calls and long ATM calls on every DIA constituent.
- **Strategy B (model-filtered):** the SAME N short DIA calls, with long calls only on the constituents the STM model
  selects. The premium left unspent is reported, never redeployed.
- **Strategy C (redeploy the unused premium):** left open.

The engine trades one of the two strategies (`dispersion.traded`, B by default). The cycle tracks the other alongside
for the comparison. It never sends an order to a broker: this is a backtest.

### Owner's choices (2026-11-16)

- **Sizing.** This is the screener's rule, `ETFShareOptionFactor.replicate`: the constituent calls copy the ETF
  calls' share exposure with the ETF's weights.
  - N is the fewest DIA calls at which every leg is at least one whole contract. It was 18 on the screener's
    2026-11-06 DIA row.
  - **N is FIXED on the full basket before the model runs.**
- **Option prices come from the factor chain** (owner 2026-11-16): IBKR's quote when there is one, else Black-Scholes
  on the underlying's close, its IBKR implied volatility and the IRX rate.
  - `ETFShareOptionValueFactor` / `CompanyShareOptionValueFactor`: the option's IBKR MIDPOINT close (quoted), else
    `ETFShareOptionModelPriceFactor` / `CompanyShareOptionModelPriceFactor`
    (`.../derivatives/option/share_option_model_price.py`).
  - σ is the underlying's `OPTION_IMPLIED_VOLATILITY` close (a 30-day ATM implied vol from IBKR). DIA's implied vol is
    below its members', so the index-vol premium is in the prices.
  - r = ln(1 + IRX/1000); q = 0; T = calendar days to expiry / 365 from the moment the close is known.
  - IBKR keeps no history of expired options, so historical legs get the model price. Each option's quotes are tried
    ONCE when the leg opens (preload service, MIDPOINT); the window is then marked covered, so the valuation never asks
    IBKR again.
  - ATM strike on a listed-style grid; bid = ask (no spread).
  - The cycle sizes the trade with the same values the engine then marks the portfolio with (`FactorOptionPricer`).
- **Everything is monthly.**
  - The trade rolls at each monthly expiry, using the screener's ~30 DTE rule.
  - The model is retrained at every roll.
  - The STM horizon is 21 sessions.

## How it runs: inside the Misbuffet engine, one daily bar at a time

`Algorithm.on_data` → `DispersionTradingCycle.step(t)` (`src/application/services/dispersion/`) works only from the
closes KNOWN at t. A daily close dated D is known from D+1 00:00 (the `MarketDataHistoryService` frontier). So the
first step after a Friday expiry sees that Friday's close.

At that step the cycle does three things:

1. **Settles the expiring trade.** A and B are settled at that close: payoffs plus the net initial premium. The
   traded legs get a target of 0 contracts, filled at their intrinsic value.
2. **Opens the next trade at the same close:**
   - members in force that day (`IndexMembership`) and their price weights;
   - a modelled ATM call for DIA and for EVERY member;
   - N computed from the full basket;
   - STM scores from closes up to that day;
   - the selection;
   - A and B.
3. **Returns the targets:** −N DIA calls and +q contracts per selected member, all whole contracts.

The algorithm then:

- sends the targets to `set_holdings`. DIA calls are `ETFShareOption`s, booked in the portfolio's
  `ETFShareOptionPortfolio` sub-portfolio (`<name>_ESO`). Members' calls are `CompanyShareOption`s, booked in the
  `CompanyShareOptionPortfolio` (`<name>_CSO`). Each leg is registered as an entity first.
- overrides `_resolve_asset_price`: an option leg gets the cycle's price at the latest known close (the value factor;
  its intrinsic value once settled). That is the price the orders fill at. The engine's daily valuation
  (`PortfolioService`) resolves the same value factors through the holding value factors.

After the run, `project_manager` writes the A vs B report (`dispersion_report.write_report`).

**Shared layers added for this project (2026-11-16):**

- **IBKR `ETFShare` / `ETFShareFactor` repositories.** DIA's bars come through `MarketDataService` like a share's. An
  earlier IBKR ETF repository was removed on 2026-05-08 with the old ETF model.
- **IBKR `ETFShareOption` / `ETFShareOptionFactor` repositories**, for the one quote attempt per option.
- **The `ETFShareOptionPortfolio` family:** portfolio, holding and sub-portfolio link, as for `CompanyShareOption`.
  Tables `etf_share_option_portfolios`, `etf_share_option_portfolio_holdings` and
  `etf_share_option_portfolio_portfolio_holdings` were created on `base_infra` on 2026-11-16, after a COPY_ONLY backup
  (`base_infra_before_eso_tables_20261116.bak`). `set_holdings`, the trade manager and the quantity lookups know it.
- **Factors:** `CompanyShareOptionModelPriceFactor`, `ETFShareOptionModelPriceFactor`, `ETFShareOptionValueFactor`
  and `ETFShareOptionPortfolioHoldingValueFactor`. `CompanyShareOptionValueFactor` falls back to its model price.

**Still open:** **WBA is no longer listed at IBKR** (delisted 2025), so it has no stored close and no implied vol. Its
options are priced with realised vol on its Eulerpool file-cache closes (`SymbolRoutedPricer`, logged), and the
engine's valuation cannot value a held WBA call.

## Structure (same as spatio_temporal_momentum_project_10m)

```
etf_dispersion_stm_project/
├── config.py                      # DEFAULT_CONFIG (engine keys + 'dispersion' / 'stm' sections), build_* helpers
├── project_manager.py             # EtfDispersionSTMProjectManager: backtest + A vs B report; CLI prices / backtest
├── data/
│   ├── dia_universe.py            # DJIA members since 2020-08-31, dated changes, splits -> IndexMembership
│   ├── universe_setup.py          # Universe + point-in-time UniverseConstituent rows (ETF included)
│   └── price_ingestion.py         # DailyHistoryUpdater (members' + DIA's IBKR bars, write-only) + file caches (WBA)
├── models/model_trainer.py        # DispersionModelTrainer(BaseModelTrainer): build_cycle
└── backtesting/
    ├── backtest_runner.py         # BacktestRunner(BaseBacktestRunner)
    ├── base_project_algorithm.py  # Algorithm(BaseProjectAlgorithm): on_data -> cycle.step -> set_holdings
    └── synthetic_demo.py          # the same cycle on synthetic closes, in-memory SQLite (tests)
```

Shared services (`src/application/services/dispersion/`):

| file | contents |
|---|---|
| `dispersion_trading_cycle.py` | the cycle, `KnownClosesReader`, `MonthResult` |
| `dispersion_portfolio_construction_service.py` | N fixed on the full basket, A / B, premiums, settlement |
| `stm_constituent_scorer.py` | the EXISTING STM pipeline refit on the members, in memory; score in [-1, 1], not a probability |
| `model_selection.py` | `minimum_model_score`, `top_n`, `bottom_n_excluded`, `percentile_threshold`; `minimum_probability_up` refused |
| `factor_option_pricer.py` | the engine's option prices from the value factors (`FactorOptionPricer`, `SymbolRoutedPricer`) |
| `modelled_option_pricing.py` | realised-vol Black-Scholes (synthetic demo, members without stored data) |
| `index_membership.py` | point-in-time membership and price weights |
| `dispersion_report.py` | the A vs B report |
| `dispersion_progress.py` | `status.json` for the `/dispersion-stm/` page |

One shared change: `WindowResult.model` in `stm_walk_forward.py` keeps the trained network.

## Data

- **Daily IBKR bars through `MarketDataService`, into `factor_values`.** Preloaded before the first bar from
  `price_history_start` (2007-01-01) by `BacktestDataPreloadService`, which needs the gateway (TWS 127.0.0.1:7497 or the
  Docker paper gateway). They cover:
  - the members' and DIA's TRADES bars and `OPTION_IMPLIED_VOLATILITY` (σ);
  - IRX (r).
- **File caches**, `results/etf_dispersion_stm/price_history/<source>/` (never written to the database). Used only for
  members IBKR no longer lists (WBA):
  - `ibkr/` was filled on 2026-11-16 by the `prices` command (read-only, client id 80).
  - `eulerpool/`: checked against IBKR, identical on most days but off by 0.1–5.8 % on scattered days.

## Run

```python
from src.application.managers.project_managers.etf_dispersion_stm_project.project_manager import (
    EtfDispersionSTMProjectManager,
)
EtfDispersionSTMProjectManager().run()       # progress: http://127.0.0.1:5000/dispersion-stm/
```

```
python -m src.application.managers.project_managers.etf_dispersion_stm_project.project_manager backtest
python -m ...project_manager prices             # refresh the IBKR file cache (Docker: scripts/dispersion_docker_job.sh)
python -m ...project_manager prices-eulerpool
```

Output goes to `results/etf_dispersion_stm/<run time>/`: `trades.csv`, `constituents.csv` and `summary.json`. The
report is rewritten after every settled month. `status.json`, `timings.csv`, `preload.csv` and the run manifest are
in `results/etf_dispersion_stm/`.

**Cost:** each roll retrains a TFT on 6 years × about 30 members, roughly 15 minutes on 4 CPU threads, so a full
2021–2026 run is about 70 rolls.

**2026-11-16:** a run with no CPU limit coincided with an unclean PC restart (Kernel-Power 41). Cap the threads,
e.g. `OMP_NUM_THREADS=4` or `torch.set_num_threads`.

Tests (all in memory, no IBKR):

- `tests/dispersion/test_model_filtered_dispersion.py`: the cycle and the project.
- `tests/component/factor_context/test_option_model_price.py`: the pricing chain and the ESO valuation.
- `tests/misbuffet/test_etf_share_option_portfolio.py`: the sub-portfolio.
- `tests/repositories/test_ibkr_etf_share_repositories.py`: the IBKR ETF / ETF option repositories.
