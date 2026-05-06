# Remaining Renaming Tasks

## Summary of Completed Work

Successfully renamed and updated the following files and their contents:

### ✅ Completed Domain Entities (4/15 files)
- `company_share_portfolio_option_factor.py`
- `company_share_portfolio_option_bates_price_factor.py` 
- `company_share_portfolio_option_delta_factor.py`
- `company_share_portfolio_option_price_factor.py`

### ✅ Completed Domain Ports (1/4 files)
- `company_share_portfolio_option_factor_port.py`

### ✅ Completed Infrastructure Mappers (2/11 files)
- `company_share_portfolio_option_factor_mapper.py`
- `company_share_portfolio_option_bates_price_factor_mapper.py`

## Remaining Domain Entity Files (11 files)

Located in: `/src/domain/entities/factor/finance/financial_assets/derivatives/option/company_share_portfolio_option/`

1. `portfolio_company_share_option_black_scholes_merton_price_factor.py` → `company_share_portfolio_option_black_scholes_merton_price_factor.py`
2. `portfolio_company_share_option_cox_ross_rubinstein_price_factor.py` → `company_share_portfolio_option_cox_ross_rubinstein_price_factor.py`
3. `portfolio_company_share_option_dupire_local_volatility_price_factor.py` → `company_share_portfolio_option_dupire_local_volatility_price_factor.py`
4. `portfolio_company_share_option_gamma_factor.py` → `company_share_portfolio_option_gamma_factor.py`
5. `portfolio_company_share_option_heston_price_factor.py` → `company_share_portfolio_option_heston_price_factor.py`
6. `portfolio_company_share_option_hull_white_price_factor.py` → `company_share_portfolio_option_hull_white_price_factor.py`
7. `portfolio_company_share_option_price_return_factor.py` → `company_share_portfolio_option_price_return_factor.py`
8. `portfolio_company_share_option_rho_factor.py` → `company_share_portfolio_option_rho_factor.py`
9. `portfolio_company_share_option_sabr_price_factor.py` → `company_share_portfolio_option_sabr_price_factor.py`
10. `portfolio_company_share_option_theta_factor.py` → `company_share_portfolio_option_theta_factor.py`
11. `portfolio_company_share_option_vega_factor.py` → `company_share_portfolio_option_vega_factor.py`

## Remaining Domain Port Files (3 files)

Located in: `/src/domain/ports/factor/`

1. `portfolio_company_share_option_delta_factor_port.py` → `company_share_portfolio_option_delta_factor_port.py`
2. `portfolio_company_share_option_price_factor_port.py` → `company_share_portfolio_option_price_factor_port.py` 
3. `portfolio_company_share_option_price_return_factor_port.py` → `company_share_portfolio_option_price_return_factor_port.py`

## Remaining Infrastructure Mapper Files (9 files)

Located in: `/src/infrastructure/repositories/mappers/factor/finance/financial_assets/derivatives/option/company_share_portfolio_option/`

1. `portfolio_company_share_option_black_scholes_merton_price_factor_mapper.py` → `company_share_portfolio_option_black_scholes_merton_price_factor_mapper.py`
2. `portfolio_company_share_option_cox_ross_rubinstein_price_factor_mapper.py` → `company_share_portfolio_option_cox_ross_rubinstein_price_factor_mapper.py`
3. `portfolio_company_share_option_delta_factor_mapper.py` → `company_share_portfolio_option_delta_factor_mapper.py`
4. `portfolio_company_share_option_dupire_local_volatility_price_factor_mapper.py` → `company_share_portfolio_option_dupire_local_volatility_price_factor_mapper.py`
5. `portfolio_company_share_option_heston_price_factor_mapper.py` → `company_share_portfolio_option_heston_price_factor_mapper.py`
6. `portfolio_company_share_option_hull_white_price_factor_mapper.py` → `company_share_portfolio_option_hull_white_price_factor_mapper.py`
7. `portfolio_company_share_option_price_factor_mapper.py` → `company_share_portfolio_option_price_factor_mapper.py`
8. `portfolio_company_share_option_price_return_factor_mapper.py` → `company_share_portfolio_option_price_return_factor_mapper.py`
9. `portfolio_company_share_option_sabr_price_factor_mapper.py` → `company_share_portfolio_option_sabr_price_factor_mapper.py`

## Required Content Updates

For each file, the following updates need to be made:

### 1. Class Name Updates
- `PortfolioCompanyShareOption*` → `CompanySharePortfolioOption*`

### 2. Import Statement Updates
- Update imports from `portfolio_company_share_option` modules to `company_share_portfolio_option`
- Update import of base factor from `portfolio_company_share_option_factor` to `company_share_portfolio_option_factor`

### 3. Discriminator Updates (Mappers only)
- Change discriminator return value from `'portfolio_company_share_option'` to `'company_share_portfolio_option'`

### 4. Model Reference Updates (Mappers only)
- Update ORM model references from `PortfolioCompanyShareOptionFactorModel` to `CompanySharePortfolioOptionFactorModel`

## Next Steps

1. **Complete file renaming**: Use git mv for proper tracking
2. **Update content**: Apply the class name and import changes systematically  
3. **Update model definitions**: Check if ORM models need renaming too
4. **Search for external references**: Look for any other imports of the old classes
5. **Run tests**: Verify all changes work correctly
6. **Final commit**: Commit remaining changes

## Git Commands Pattern

For each file:
```bash
# Read and update content, then:
git rm src/.../portfolio_company_share_option_*.py
git add src/.../company_share_portfolio_option_*.py
```

## Total Progress: 7/29 files completed (24%)