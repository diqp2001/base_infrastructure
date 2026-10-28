# Factor research, factor value generation and factor analysis of project results

Added 2026-10-28. Three capabilities on the Flask app, all computed by application services.

| Page | What |
|---|---|
| `/powerbuffet` → "Factor research" card | links to the three pages below |
| `/powerbuffet/generate` | factor value generation for a universe, interval, frequency (background job) |
| `/powerbuffet/research` | factor research: correlations, primary factor, relationships, quantile portfolios, IC |
| `/factor-analysis/?source=<key>` | CAPM / Fama-French 3 / 5 / custom regression of a project's returns; embedded as the "Factor Analysis" section of every results page (`/stm/results`, `/csm/results`, `/spx_v2/results`, `/strategies/experiments/<id>/report`) |

## Layers

| Layer | Files |
|---|---|
| Domain | `domain/entities/research/factor_models.py` — CAPM / FF3 / FF5 factor lists, series kinds (external, market proxy, mimicking portfolio), return conventions (total vs excess), analysis frequencies |
| Application | `application/services/research/`: `statistics.py` (correlations, quantile portfolios, forward returns, OLS + Newey-West, rolling OLS), `factor_research.py`, `factor_generation.py` (+ worker and job store), `project_returns.py` (strategy returns of every results source), `factor_returns.py` (factor return series, local market proxy), `factor_regression.py`, `research_renderer.py`, `research_services.py` |
| Infrastructure | `infrastructure/research/factor_return_files.py` (CSV + JSON store under `data/factor_returns/`, not committed; Kenneth R. French importer); `FactorValueRepository.get_values_panel` |
| Interfaces | `factor_analysis_controller.py` (`/factor-analysis`), `factor_research_controller.py` (`/powerbuffet/generate`, `/powerbuffet/research`), templates `factor_*.html`, `research_base.html`, `_factor_analysis_section.html` |

## Methodology

**Generation.**
- *Eligible factors:* only calculated factors defined at the requested frequency. Another frequency, or a raw IBKR series, is refused with the reason.
- *When and for whom:* values are stamped at the close of each NYSE bar, and computed only while the share is a universe member at that time.
- *How:* through `FactorValueResolutionService`, which reads closed bars only and stored data only.
- *Idempotent:* existing values are counted and kept, never overwritten ("updated" is always 0).
- *Execution:* each run is a separate process with a JSON status file in `results/research_jobs/`. Only one job per identical scope can run at a time.

**Research.**
- *Membership:* point-in-time; values count only while the share is a constituent.
- *Timestamps:* mapped to their bar. A factor stamped t is paired with the return from the close of its bar onward, so it is never paired with an earlier return.
- *Three correlation notions, kept apart:*
  - pooled, over all security-time pairs;
  - cross-sectional, one per timestamp and then summarised (mean, median, std, t, share positive, first vs second half);
  - time series, between the long-short portfolio returns of two factors.
- *Quantile portfolios:*
  - equal weight, rebalanced every bar, held one bar;
  - Sharpe computed without the risk-free rate;
  - value weighting is unavailable because no market capitalisation is stored.
- *Information coefficient:* Spearman, per timestamp, for the chosen horizons.
- *Long-short series:* it can be saved as a custom factor return, re-stamped at the bar where each return is realised.

**Factor analysis.**
- *Return stamping:* STM and cross-sectional reports stamp a return at the decision, but it is earned over the next bar. Each return is re-stamped at the bar where it is realised (NYSE grid) before compounding to daily, weekly or monthly. SPX v2 returns come from the account equity and are already realised-stamped.
- *Risk-free rate:* subtracted exactly once, and only for total-return strategies (long-only, SPX). Long/short and position-scaled strategies are self-financing (excess returns). The default can be overridden.
- *Sample:* aligned periods only, never filled. The periods without factor data are counted and reported.
- *Estimation:* OLS with Newey-West errors (Bartlett kernel, lags from the n^(2/9) rule). Student t inference with n−k degrees of freedom.
- *Reporting:*
  - alpha annualised arithmetically;
  - additive contributions (model-based, not causal);
  - rolling regressions, residual diagnostics and outliers;
  - comparisons on one common sample;
  - warnings when the sample is short or the factors are near-collinear.

**Factor return data.**
- *Fama-French:* the daily 3 and 5 factors are imported from the Kenneth R. French data library (percent converted to decimal). It is published with a lag of one to two months.
- *CSV import:* a user CSV can be imported.
- *Local market proxy:* `local_market` builds MKT_RF = SPY return − RF, with RF = IRX(t−1)/10/100/252. It is labelled as a proxy, not the academic Mkt-RF.
- *Missing data:* factor returns are never fabricated. An analysis outside the data's coverage is refused with the dates.

## Known limitations

- **Value weighting:** value-weighted portfolios need market capitalisation, which isn't stored.
- **Generation speed:** generation calls the resolver once per value. Large universes over long intervals are slow; the job reports progress and can be stopped.
- **Generation inputs:** generation never fetches missing raw data from IBKR. Use the data preload first.
- **Intraday factor analysis:** analysing an intraday project against daily Fama-French factors needs enough trading days; a one-week backtest gives about 5 observations, and the page warns.
- **Compounding long-short factors:** compounding daily long-short factor returns into weekly or monthly periods is the usual approximation; the French monthly files are not imported.
