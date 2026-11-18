# Eulerpool repositories (Fundamentals API)

Eulerpool (https://api.eulerpool.com/api/1, SEC XBRL data) as a data source of the factor pipeline, like `fmp_repo`
and `ibkr_repo`. Added 2026-11-13. Only the Eulerpool-specific part lives here: HTTP, the endpoints, and the mapping of
XBRL facts into the canonical statements. Factor values come from the SHARED `StatementFactorValueRepository`
(`fundamental_provider/`), so there is no Eulerpool factor value class.

```
Eulerpool API -> EulerpoolClient -> EulerpoolFundamentalsRepository (8 endpoints, XBRLFact)
  -> Eulerpool{IncomeStatement,BalanceSheet,CashFlowStatement}Repository (FinancialStatementSourcePort: canonical
     StatementRecord) -> StatementFactorValueRepository('eulerpool') (FactorValueProviderPort, family 'eulerpool')
  -> raw CompanyShareFactor series (source 'eulerpool') -> the same calculated fundamental factors -> FactorValue
```

```
eulerpool_repo/
├── eulerpool_client.py            EulerpoolClient: Bearer key, pacing, retry on 429 / 5xx, errors
│                                  (EulerpoolAuthenticationError 401/403, EulerpoolNotFound 404, EulerpoolRateLimitError
│                                  429, EulerpoolUnavailable 5xx / network, EulerpoolResponseError), identifier_path
├── base_eulerpool_repository.py   BaseEulerpoolRepository (client + factory, symbol_of = the ticker)
└── fundamentals/
    ├── eulerpool_fundamentals_repository.py      get_income_statement / get_balance_sheet / get_cash_flow /
    │                                             get_financial_facts / search_xbrl_facts / get_financial_ratios /
    │                                             get_company_info / get_annual_report
    └── eulerpool_financial_statement_repository.py  TAG_MAP (XBRL tag -> canonical field), quarter derivations,
                                                  point-in-time availability
```

## Key, configuration, quota
- Key: `EULERPOOL_API_KEY`, else `api_key` in `EULERPOOL_CREDENTIALS_FILE` (default `../eulerpool_credentials.json`,
  outside the repository, like `../FPM_credentials.json`). Sent as `Authorization: Bearer`; never in a URL, an error or
  a log line. Base URL: `EULERPOOL_BASE_URL`, else `https://api.eulerpool.com/api/1`.
- Quota (checked 2026-11-13): 100,000 requests a month (`x-ratelimit-*` headers -> `client.rate_limit`). Covers the
  whole CSM paper universe (PNC, the regional banks, insurers) that FMP's plan does not.
- Off by default: `RepositoryFactory(session, eulerpool_client=client)` or `factory.create_eulerpool_repositories()`
  sets `_available_repository_families['eulerpool'] = True`. Bulk load:
  `factory.factor_value_eulerpool_repo.load_company(share)`.

## What the API serves (checked live 2026-11-13)
- Statements `/fundamentals/financials/{id}/income-statement | balance-sheet | cash-flow`, filters `fiscal_period`
  (FY, Q1..Q4) and `form` (10-K, 10-Q): SEC XBRL facts `{cik, ticker, taxonomy, tag, period_end, fiscal_year,
  fiscal_period, form, val, unit, filed, updated_at}`, at most 1000 rows (no paging, `limit` ignored) - asked per
  fiscal period type. ONE row per (tag, period end, form): for a period older than the latest, the LATEST filing that
  repeated it (next year's comparative), so `filed` / `fiscal_year` / `fiscal_period` are that filing's. No period
  start. 8-K press-release rows too (not used).
- `/fundamentals/financials/{id}` (all facts, `tag`, `limit` <= 2000) and `/fundamentals/facts/search` (`tag`
  required, latest value per company): no filing date -> reference / mapping data, never factor values.
- `/fundamentals/financials/{id}/ratios`: the latest fiscal year only (pe, pb, debt_to_equity, roe, profit_margin) -
  no history, so not a point-in-time series; the calculated factors compute these from the statements.
- `/fundamentals/company/{id}`: SEC company data (`CompanyInfo`) - answered HTTP 500 for every identifier tried on
  2026-11-13. Not stored (the share entities have no CIK / SIC fields).
- `/fundamentals/annual-report/{id}?year=`: the 10-K as JSON (`AnnualReport.report`, raw document data).
- Identifiers: ticker, ISIN, CUSIP, SEDOL, WKN; the share entities carry the ticker only.

## Canonical statements (eulerpool_financial_statement_repository.py)
- `TAG_MAP`: canonical field (`STATEMENT_FIELDS`) -> alternatives of signed tags (all required; first complete one).
  Canonical signs: cash paid out negative (capex, buybacks, dividends, acquisitions), a receivables / inventory
  increase lowers operating cash. `netIncome` falls back to `ProfitLoss` (incl. noncontrolling interests) when the
  parent's `NetIncomeLoss` is missing (PNC's 10-Qs) - an approximation, removable in one line. Fields Eulerpool does
  not serve (totalDebt, ebitda, incomeBeforeTax, weighted shares, ...) are absent: factors reading them have no value.
- Facts used: 10-Q / 10-K, per (tag, period end) the earliest filed. FY facts must end on the fiscal year end (anchor:
  the latest 10-K period, +-10 days); Q facts must not (a 10-Q repeats the last year end's balances).
- Durations: income statement 10-Q = the quarter, cash flow 10-Q = year to date. Quarterly series: IS Q4 = FY -
  Q1..Q3; CF Q2/Q3 = YTD differences, Q4 = FY - YTD3; balance Q4 = the year end. Per-share and share-count fields are
  not derived (no Q4 EPS: TTM per-share measures have no value; the annual ones do). An IS 10-K row whose revenue is
  below Q1 + Q2 + Q3 is the fourth quarter (selected quarterly data): the year is rebuilt from the four quarters.
- Point in time (owner's choice 2026-11-13): public at min(filed + 1 day, period end + SEC deadline + 1 day), deadline
  = 10-Q 45 + 5 days, 10-K 90 + 15 days (`StatementRecord.available_by`); a derived value when its last component is.
  Never before an on-time filer's filing. Gaps: a restated figure replaces the first published one; a late filer
  beyond the extension would be early.
- Requests: 4 per statement (FY, Q1, Q2, Q3), cached for the session -> 12 per share for everything.

## Source selection
Statement factors read `STATEMENT_SOURCES = ("fmp", "eulerpool")`: one provider per value, FMP first (exact acceptance
times), Eulerpool when FMP yields nothing (402 symbols). The resolver creates the series of every ENABLED provider and
reads them in that order (`_missing_sources`, `_series_by_source`) - no provider name in application code.

## Daily prices (prices/eulerpool_price_history.py, 2026-11-16)

`EulerpoolPriceHistory` implements the dispersion `PriceHistoryPort` on `GET /charting/ohlcv/{id}?resolution=D`.

- Daily bars go back to 1989. The trading day is the bar stamp's UTC date.
- It serves stocks only: DIA, SPY and DIA's ISIN all return 404.
- Quality, checked against IBKR over 13 months: most closes are identical, but scattered days are off by 0.1 to 5.8 %.
  Use it as a fallback only.
- Intraday bars cover only about the last week.

## Users
- `etf_dispersion_stm_project` (2026-11-16): daily-close fallback for members IBKR no longer lists. File cache only.
- `cross_sectionnal_project_10m` (2026-11-16): fundamental candidates of the classifier through
  `RepositoryFactory.enable_provider_family('eulerpool')` and the statement repositories (in-memory, nothing stored).

## Tests
`tests/eulerpool/` (fake Eulerpool session, in-memory SQLite): client, endpoints, canonical statements, pipeline
(raw value, gross margin, FCF, growth, ROE, FMP / Eulerpool selection, IBKR + FMP + Eulerpool in one factor).
