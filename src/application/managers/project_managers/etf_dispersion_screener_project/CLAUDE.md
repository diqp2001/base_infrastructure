# ETF dispersion-option screener

Screens US-listed equity ETFs with fewer than 50 constituents for a potential long-dispersion trade: short one ATM
call on the ETF, long ATM calls on every constituent, weighted by the ETF weights and scaled to dollar-delta
neutrality. It is a screen for a potential dispersion trade, not an arbitrage. The progress, decisions and plan
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

## Rules
- Use executable bid/ask prices and whole option contracts. Fractional sizing is a reference only.
- Never mix stale and current data. Name every exception, such as a different expiry or a missing chain.
- Downloads are polite: one file at a time, at most one per second, once per ETF per day.
- Tests: `tests/dispersion/`. They use inline issuer files and in-memory SQLite, and never download anything.
