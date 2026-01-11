# Local Repositories

This directory contains local repository implementations that mirror the structure of all models in `src/infrastructure/models/`.

## Structure

The repository structure follows the same hierarchy as the infrastructure models:

```
repositories/local_repo/
├── continent/
│   └── continent_local_repo.py
├── country/
│   └── country_local_repo.py
├── industry/
│   └── industry_local_repo.py
├── sector/
│   └── sector_local_repo.py
├── factor/
│   ├── factor_local_repo.py
│   ├── factor_model_local_repo.py
│   └── factor_value_local_repo.py
├── finance/
│   ├── company_local_repo.py
│   ├── exchange_local_repo.py
│   ├── market_data_local_repo.py
│   ├── portfolio_local_repo.py
│   ├── position_local_repo.py
│   ├── security_holding_local_repo.py
│   ├── financial_assets/
│   │   ├── bond_local_repo.py
│   │   ├── cash_local_repo.py
│   │   ├── commodity_local_repo.py
│   │   ├── company_share_local_repo.py
│   │   ├── crypto_local_repo.py
│   │   ├── currency_local_repo.py
│   │   ├── derivatives_local_repo.py
│   │   ├── equity_local_repo.py
│   │   ├── etf_share_local_repo.py
│   │   ├── financial_asset_local_repo.py
│   │   ├── forward_contract_local_repo.py
│   │   ├── future_local_repo.py
│   │   ├── index_local_repo.py
│   │   ├── options_local_repo.py
│   │   ├── portfolio_company_share_option_local_repo.py
│   │   ├── security_local_repo.py
│   │   ├── share_local_repo.py
│   │   └── swap/
│   │       ├── currency_swap_local_repo.py
│   │       ├── interest_rate_swap_local_repo.py
│   │       ├── swap_leg_local_repo.py
│   │       └── swap_local_repo.py
│   ├── financial_statements/
│   │   ├── balance_sheet_local_repo.py
│   │   ├── cash_flow_statement_local_repo.py
│   │   ├── financial_statement_local_repo.py
│   │   └── income_statement_local_repo.py
│   ├── holding/
│   │   ├── holding_local_repo.py
│   │   ├── portfolio_company_share_holding_local_repo.py
│   │   └── portfolio_holding_local_repo.py
│   └── back_testing/
│       ├── back_testing_data_types_local_repo.py
│       ├── enums_local_repo.py
│       └── financial_assets/
│           └── symbol_local_repo.py
└── time_series/
    ├── time_series_local_repo.py
    └── finance/
        ├── financial_asset_time_series_local_repo.py
        └── stock_time_series_local_repo.py
```

## Purpose

Each local repository provides:

- **In-memory storage**: Uses simple lists for data persistence
- **Basic CRUD operations**: `save()`, `find_by_id()`, `find_all()`
- **Model mirroring**: Each repository corresponds to a specific infrastructure model
- **Repository pattern**: Implements common repository interface methods

## Usage

Each repository follows the same pattern:

```python
# Example usage
repo = CompanyLocalRepository()

# Save entity
repo.save(company_instance)

# Find by ID
company = repo.find_by_id(123)

# Find all
all_companies = repo.find_all()
```

## Notes

- All repositories use in-memory storage (list-based)
- No persistence between application restarts
- Suitable for testing and development scenarios
- Mirrors the exact structure of `src/infrastructure/models/`