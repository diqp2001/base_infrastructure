# ETF dispersion-option screener

Screens US-listed equity ETFs with fewer than 50 constituents for a potential long-dispersion trade: short one ATM
call on the ETF, long ATM calls on every constituent, copying the ETF's holdings. It is a screen for a potential dispersion trade. The progress, decisions and plan
are in `docs/dispersion_screening_progress.txt`.

## Layout
- **This folder** holds orchestration only. `config.py` holds every setting: `SCREEN` is a
  `DispersionScreenConfig`, plus the data sources and folders. `project_manager.py` runs a screening date.
- **Domain rules** (pure): `src/domain/entities/finance/dispersion/`
  - `etf_holdings.py`: listings, holdings snapshots, constituent rules.
  - `screen_config.py`.
  - `option_data.py`, `option_selection.py` (expiry, ATM strike), `quote_checks.py`.
  - `dispersion_trade.py`: sizing, premium, implied correlation, scenarios.
- **Ports:** `src/domain/ports/finance/dispersion/`. Every method takes the screening date.
- **Issuer adapters:** `src/infrastructure/repositories/issuer_repo/` (iShares CSV, SPDR XLSX). Every
  downloaded file is archived under `results/etf_dispersion_screener/holdings_archive/`. The issuers serve the
  latest day only, so this archive is the holdings history.
- **IBKR option data:** `src/infrastructure/repositories/ibkr_repo/finance/dispersion/`. It is read-only, on its
  own client id (77), and uses streaming quotes only (no snapshot fees). A gateway that does not answer raises
  `MarketDataUnavailable`. That is never read as "not found".
- **Services:** `src/application/services/dispersion/`: `EtfUniverseService`, `DispersionScreeningService`.
- **UI/API:** the `/dispersion/` Flask blueprint (`dispersion_controller.py`). It reads the results files.
- **Entities:**
  - `ETFShare` is the fund.
  - `ETFShareOption` and `CompanyShareOption` both inherit from `ShareOption`.

## Run
```
python -m src.application.managers.project_managers.etf_dispersion_screener_project.project_manager [YYYY-MM-DD]
```
Output: `results/etf_dispersion_screener/<date>/universe.json`, `universe.csv` and `run_manifest.json`.
With `DISPERSION_IBKR_HOST` (plus `_PORT` and `_CLIENT_ID`) set, the run also writes `candidates.json` and
`candidates.csv`, ranked. Quotes after the close are frozen and are refused unless `DISPERSION_ALLOW_FROZEN=yes`,
which is for diagnostics only. IBKR serves current data only, so a past date raises `HistoricalDataUnavailable`.
Each run saves its contract lookups to `<date>/lookups.json`. A later run on the same date reuses them and
requests quotes only. Do the heavy lookups while the STM trader (same paper gateway) is idle.
`DISPERSION_VALIDATE_AFTER_SECONDS` turns on the P.11 fill check: the best priced candidates are re-quoted and
written to `validation.json` and `validation.csv`. It is read-only and never sends an order.

Maturities view, per ETF:
- The "Maturities" button on `/dispersion` opens `/dispersion/etf/<T>/maturities`. Its "Run" button starts
  `maturities.py`, which prices the strategy at every expiry that the ETF and all its constituents list
  (`maturities_min_dte` to `maturities_max_dte`).
- The paper gateway publishes no port, so the job runs on its Docker network through
  `scripts/dispersion_docker_job.sh`, launched by `job_launcher` (default `wsl -d Ubuntu -- bash`). It is
  read-only, uses client id 79, and only one job runs at a time.
- It writes `<date>/maturities/<T>.json` and a status file. The page shows only maturities with a bid and an ask
  on the ETF call and on every constituent call; the others are listed as hidden.
- After the close it uses frozen quotes and labels them so.

6-month realized payoff history (a separate layer: it never changes the live screen):
- "Compute 6M history" on `/dispersion` starts `realized_history.py` for every eligible ETF. It is read-only and
  uses client id 80.
- It opens the screen's trade on every trading day of the last 6 months: the ATM ETF call and ATM constituent calls
  struck at that day's close, weighted by `replicate()`, with the expiry from `select_expiry` on the monthly
  expiries. It then holds the trade to that expiry.
- It writes `<date>/history/<T>.json` and `summary.json`. The formulas are in
  `src/domain/entities/finance/dispersion/realized_payoff.py`.
- Prices are IBKR daily TRADES closes (split-adjusted), cached under `price_history/`.
- Holdings come from the archived snapshots, so they are point in time from 2026-11-05 on. Before that, the earliest
  snapshot is back-cast and flagged (survivorship).

## Rules
- The strategy is 1 short ATM ETF call against long ATM calls on every constituent, with the same expiry. The long
  calls copy the ETF's holdings: an ETF share holding 5 shares of A gives 5 A calls per ETF call (100 shares).
  Positions are fractions of a contract; `whole_contract_etf_calls` shows the size at which every leg is whole.
- Cost uses the broker's prices as quoted: the ETF call is sold at its bid and every constituent call is bought at its
  ask. An opportunity is a net premium (ETF proceeds minus constituent cost) of 0 or more (owner, 2026-11-06).
- The ETF call needs a bid and every constituent call needs an ask. There is no spread limit. Greeks, dollar delta
  and mids are information only.
- Never mix stale and current data. Name every exception, such as a different expiry or a missing chain.
- Downloads are polite: one file at a time, at most one per second, once per ETF per day.
- Tests: `tests/dispersion/`. They use inline issuer files and in-memory SQLite, and never download anything.

## Dispersion factor values (2026-11-10)
Owner: dispersion as factor values in the factor value table, produced like the CompanyShare factors (no new table);
realized and implied are two separate factors (ETFShareRealizedDispersionFactor, ETFShareImpliedDispersionFactor).
`dispersion_factors.py`:
- `prices <date>` (Docker, IBKR read-only, client id 80): 13 months of daily closes into the price cache.
- `quotes <date>` (Docker, IBKR read-only, client id 80, market hours, streaming quotes - no snapshot fee): the ATM
  call and put of every covered ETF and constituent for the expiries closest to 1..6 months ->
  results/<date>/atm_options/<time>.json.
- `load <date> [--tickers] [--measures] [--every N] [--no-realized] [--no-implied]` (Windows, base_infra; files only):
  the ETFShare / CompanyShare rows, the holdings as UniverseConstituent rows (`"<SYMBOL> holdings"` investment
  universe, each snapshot from its date; before the first snapshot back-cast and said so in the universe description),
  the closes and the ATM series as raw factor values, then FactorValueResolutionService resolves and stores the
  realized values (trading days of the last 6 months) and the implied values (each quote run's time).
- An ETF with a constituent without prices (e.g. a share not listed in the US) is skipped, nothing written.
- IBKR has no history of expired options (and listed ones only in intraday bars): the implied series starts with the
  first quote run (2026-11-10).
