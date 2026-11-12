# FMP repositories (Financial Modeling Prep)

The counterpart of `ibkr_repo` for FMP: FMP is requested and normalized here, values are stored through the local
repositories, and `FactorValueResolutionService` reaches FMP as a repository family (`'fmp'`), like `'ibkr'`.

```
fmp_repo/
├── fmp_client.py                     FMPClient: /stable GET, key, pacing, errors (FMPAuthenticationError 401/403,
│                                     FMPSubscriptionError 402, FMPRateLimitError 429, FMPUnavailable, FMPResponseError)
├── base_fmp_repository.py            BaseFMPRepository (client + factory, symbol_of)
├── finance/financial_statements/
│   └── fmp_financial_statement_repository.py
│                                     FMPIncomeStatement / FMPBalanceSheet / FMPCashFlowStatement repositories ->
│                                     StatementRecord (the filing's data + the fields as floats)
├── factor/
│   └── fmp_factor_value_repository.py
│                                     FMPFactorValueRepository: records -> raw fundamental factor values; the
│                                     resolution service's hook _fetch_factor_value_from_fmp
└── fmp_repository.py                 legacy quote / profile translator (not used by the factor pipeline)
```

## Key and plan
- Key: `FMP_API_KEY`, else `api_key` in `FMP_CREDENTIALS_FILE` (default `../FPM_credentials.json`, next to the repo).
  Never logged: errors name the endpoint and parameters without it.
- Current plan (checked 2026-11-12): statements quarterly and annual, `limit` <= 5 per request, a subset of large US
  symbols (e.g. AAPL, MSFT, JPM, XOM, KO, TGT, SHOP; not GBCI, HOMB, AEP, ASML: 402), TTM endpoints 402,
  as-reported statements 402. Quarters are asked one fiscal quarter at a time (period=Q1..Q4, 5 each = 20 quarters),
  years with period=FY (5 years). One share = 13 requests for the three statements at both frequencies.

## Enabling it
FMP is off by default (no request by surprise): `RepositoryFactory(session, fmp_client=client)` or
`factory.create_fmp_repositories()` (the configured key) sets `_available_repository_families['fmp'] = True`.
Then a raw `fmp` series with no value known at the decision time loads that statement's whole history once per
(share, statement, frequency) and session. Bulk load: `factory.factor_value_fmp_repo.load_company(share)`.

## Storage (see src/domain/entities/factor/CLAUDE.md "Company financial statement factors")
Raw series: `CompanyShareFactor`, group `fundamental`, subgroup `income_statement | balance_sheet | cash_flow`,
frequency `1q | 1y`, source `fmp`, name = the FMP field. Each value is stamped at the filing's acceptance time
(`acceptedDate`; else the day after `filingDate`), never at the period's end. The filing's data are stored on every
statement at the same stamp: `date` (period end), `filingDate`, `acceptedDate`, `fiscalYear`, `period`,
`reportedCurrency`, `cik` (data type string / integer). `add_bulk`: a stored value is never overwritten.

## Tests
`tests/fmp/` (fake FMP session, in-memory SQLite): client, statements, factor formulas, end to end.
