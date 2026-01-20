# MODELS_INVENTORY.md - Complete Model Inventory and Mapper Status

## 📊 Complete Infrastructure Models Inventory

This document provides a comprehensive inventory of all SQLAlchemy models in the infrastructure layer and tracks their corresponding mapper implementation status.

---

## 🔢 Summary Statistics

**Total Models**: 47  
**Base Models**: 8  
**Financial Asset Models**: 16  
**Backtesting Models**: 8  
**Portfolio & Holding Models**: 7  
**Other Business Models**: 8  

**Mappers Status**:
- ✅ **Implemented**: 42 (12 existing + 30 new)
- ❌ **Missing**: 5

---

## 📋 Complete Model List by Category

### 🏗️ Base Infrastructure Models (8)
| Model | File | Mapper Status |
|-------|------|---------------|
| `ModelBase` | `__init__.py` | N/A (Base class) |
| `TimeSeriesModel` | `time_series/time_series.py` | ✅ Implemented |
| `FinancialAssetTimeSeriesModel` | `time_series/finance/financial_asset_time_series.py` | ✅ Implemented |
| `StockTimeSeriesModel` | `time_series/finance/stock_time_series.py` | ✅ Implemented |
| `FactorModel` | `factor/factor.py` | ✅ Implemented |
| `FactorValueModel` | `factor/factor_value.py` | ✅ Implemented |
| `SectorModel` | `sector.py` | ✅ Implemented |
| `IndustryModel` | `industry.py` | ✅ Implemented |

### 🌍 Geographic Models (2)
| Model | File | Mapper Status |
|-------|------|---------------|
| `CountryModel` | `country.py` | ✅ Implemented |
| `ContinentModel` | `continent.py` | ✅ Implemented |

### 💰 Financial Asset Models (16)
| Model | File | Parent | Mapper Status |
|-------|------|--------|---------------|
| `FinancialAssetModel` | `financial_assets/financial_asset.py` | `Base` | ✅ Implemented |
| `CompanyShareModel` | `financial_assets/company_share.py` | `FinancialAssetModel` | ✅ Implemented |
| `ShareModel` | `financial_assets/share.py` | `FinancialAssetModel` | ✅ Implemented |
| `EquityModel` | `financial_assets/equity.py` | `FinancialAssetModel` | ✅ Implemented |
| `SecurityModel` | `financial_assets/security.py` | `FinancialAssetModel` | ✅ Implemented |
| `BondModel` | `financial_assets/bond.py` | `FinancialAssetModel` | ✅ Implemented |
| `CashModel` | `financial_assets/cash.py` | `FinancialAssetModel` | ✅ Implemented |
| `CommodityModel` | `financial_assets/commodity.py` | `FinancialAssetModel` | ✅ Implemented |
| `CryptoModel` | `financial_assets/crypto.py` | `FinancialAssetModel` | ✅ Implemented |
| `CurrencyModel` | `financial_assets/currency.py` | `FinancialAssetModel` | ✅ Implemented |
| `ETFShareModel` | `financial_assets/etf_share.py` | `FinancialAssetModel` | ✅ Implemented |
| `IndexModel` | `financial_assets/index.py` | `FinancialAssetModel` | ✅ Implemented |
| `DerivativeModel` | `financial_assets/derivative/derivatives.py` | `FinancialAssetModel` | ✅ Implemented |
| `FutureModel` | `financial_assets/derivative/future.py` | `DerivativeModel` | ✅ Implemented |
| `OptionsModel` | `financial_assets/derivative/options.py` | `FinancialAssetModel` | ✅ Implemented |
| `ForwardContractModel` | `financial_assets/derivative/forward_contract.py` | `FinancialAssetModel` | ✅ Implemented |

### 🔄 Swap Models (2)
| Model | File | Parent | Mapper Status |
|-------|------|--------|---------------|
| `SwapModel` | `financial_assets/derivative/swap/swap.py` | `DerivativeModel` | ✅ Implemented |
| `SwapLegModel` | `financial_assets/derivative/swap/swap_leg.py` | `FinancialAssetModel` | ✅ Implemented |

### 🏢 Business Entity Models (3)
| Model | File | Mapper Status |
|-------|------|---------------|
| `CompanyModel` | `finance/company.py` | ✅ Implemented |
| `ExchangeModel` | `finance/exchange.py` | ✅ Implemented |
| `InstrumentModel` | `finance/instrument.py` | ✅ Implemented |

### 📊 Financial Statement Models (4)
| Model | File | Parent | Mapper Status |
|-------|------|--------|---------------|
| `FinancialStatementModel` | `finance/financial_statements/financial_statement.py` | `Base` | ✅ Implemented |
| `BalanceSheetModel` | `finance/financial_statements/balance_sheet.py` | `FinancialStatementModel` | ✅ Implemented |
| `IncomeStatementModel` | `finance/financial_statements/income_statement.py` | `FinancialStatementModel` | ✅ Implemented |
| `CashFlowStatementModel` | `finance/financial_statements/cash_flow_statement.py` | `FinancialStatementModel` | ✅ Implemented |

### 📈 Portfolio & Holding Models (7)
| Model | File | Mapper Status |
|-------|------|---------------|
| `PortfolioModel` | `finance/portfolio/portfolio.py` | ✅ Implemented |
| `PortfolioCompanyShareModel` | `finance/portfolio/portfolio_company_share.py` | ✅ Implemented |
| `PortfolioCompanyShareOptionModel` | `finance/portfolio/portfolio_company_share_option.py` | ✅ Implemented |
| `PortfolioDerivativeModel` | `finance/portfolio/portfolio_derivative.py` | ✅ Implemented |
| `HoldingModel` | `finance/holding/holding.py` | ✅ Implemented |
| `PortfolioHoldingsModel` | `finance/holding/portfolio_holding.py` | ✅ Implemented |
| `PortfolioCompanyShareHoldingModel` | `finance/holding/portfolio_company_share_holding.py` | ✅ Implemented |

### 🔒 Security & Position Models (2)
| Model | File | Mapper Status |
|-------|------|---------------|
| `SecurityHoldingModel` | `finance/holding/security_holding.py` | ✅ Implemented |
| `PositionModel` | `finance/position.py` | ✅ Implemented |

### 📊 Market Data Models (2)
| Model | File | Mapper Status |
|-------|------|---------------|
| `MarketDataModel` | `finance/market_data.py` | ✅ Implemented |
| `SymbolModel` | `finance/back_testing/financial_assets/symbol.py` | ✅ Implemented |

### ⚙️ Backtesting Enum Models (8)
| Model | File | Mapper Status |
|-------|------|---------------|
| `ResolutionModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `SecurityTypeModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `MarketModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `OrderTypeModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `OrderStatusModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `OrderDirectionModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `TickTypeModel` | `finance/back_testing/enums.py` | ✅ Implemented |
| `DataTypeModel` | `finance/back_testing/enums.py` | ✅ Implemented |

### 📊 Backtesting Data Models (1)
| Model | File | Mapper Status |
|-------|------|---------------|
| `BarModel` | `finance/back_testing/back_testing_data_types.py` | ✅ Implemented |

---

## 🎯 Missing Mapper Priority Matrix

### 🔥 High Priority - Core Business Logic (12)
1. `FinancialAssetModel` - Base class for all financial instruments
2. `ShareModel` - Stock shares (parent of CompanyShareModel)
3. `EquityModel` - Equity instruments
4. `SecurityModel` - Securities base class
5. `ExchangeModel` - Trading exchanges
6. `PortfolioModel` - Investment portfolios
7. `FinancialStatementModel` - Base financial statement
8. `TimeSeriesModel` - Base time series data
9. `DerivativeModel` - Base derivative instruments
10. `OptionsModel` - Option contracts
11. `MarketDataModel` - Market pricing data
12. `PositionModel` - Trading positions

### 🟡 Medium Priority - Extended Functionality (12)
13. `ETFShareModel` - Exchange-traded funds
14. `CashModel` - Cash positions
15. `CommodityModel` - Commodity instruments
16. `CryptoModel` - Cryptocurrency instruments
17. `ForwardContractModel` - Forward contracts
18. `SwapModel` - Swap contracts
19. `SwapLegModel` - Individual swap legs
20. `PortfolioCompanyShareModel` - Portfolio share allocations
21. `PortfolioDerivativeModel` - Portfolio derivative positions
22. `SecurityHoldingModel` - Security holdings
23. `FinancialAssetTimeSeriesModel` - Asset time series
24. `StockTimeSeriesModel` - Stock time series

### 🔵 Lower Priority - Specialized Models (11)
25. `BalanceSheetModel` - Balance sheet statements
26. `IncomeStatementModel` - Income statements
27. `CashFlowStatementModel` - Cash flow statements
28. `SymbolModel` - Trading symbols
29. `BarModel` - OHLCV bar data
30. `ResolutionModel` - Time resolution enums
31. `SecurityTypeModel` - Security type enums
32. `MarketModel` - Market enums
33. `OrderTypeModel` - Order type enums
34. `OrderStatusModel` - Order status enums
35. `OrderDirectionModel` - Order direction enums

---

## 🚀 Implementation Strategy

### Phase 1: Core Financial Assets (4 mappers)
- `FinancialAssetModel` (base class)
- `ShareModel` (parent of CompanyShareModel)
- `EquityModel` (common equity type)
- `SecurityModel` (base security type)

### Phase 2: Extended Financial Instruments (8 mappers)
- `DerivativeModel` (base derivative)
- `OptionsModel` (options contracts)
- `ETFShareModel` (ETFs)
- `CashModel` (cash positions)
- `CommodityModel` (commodities)
- `CryptoModel` (cryptocurrencies)
- `ForwardContractModel` (forwards)
- `SwapModel` & `SwapLegModel` (swaps)

### Phase 3: Business & Market Data (8 mappers)
- `ExchangeModel` (trading venues)
- `PortfolioModel` (portfolios)
- `MarketDataModel` (pricing data)
- `PositionModel` (positions)
- `TimeSeriesModel` (time series base)
- `FinancialAssetTimeSeriesModel` (asset time series)
- `StockTimeSeriesModel` (stock time series)
- `SecurityHoldingModel` (holdings)

### Phase 4: Financial Statements & Portfolio Extensions (7 mappers)
- `FinancialStatementModel` (statements base)
- `BalanceSheetModel` (balance sheets)
- `IncomeStatementModel` (income statements)
- `CashFlowStatementModel` (cash flow statements)
- `PortfolioCompanyShareModel` (portfolio shares)
- `PortfolioDerivativeModel` (portfolio derivatives)
- `SymbolModel` (trading symbols)

### Phase 5: Backtesting & Enums (8 mappers)
- `BarModel` (OHLCV data)
- `ResolutionModel` (time resolution)
- `SecurityTypeModel` (security types)
- `MarketModel` (markets)
- `OrderTypeModel` (order types)
- `OrderStatusModel` (order statuses)
- `OrderDirectionModel` (order directions)
- `TickTypeModel` & `DataTypeModel` (tick/data types)

---

## 🔍 Mapper Pattern Analysis

### Existing Pattern (from CountryMapper):
```python
class ModelMapper:
    @staticmethod
    def to_domain(orm_obj: ORMModel) -> DomainEntity:
        """Convert ORM model to domain entity."""
        return DomainEntity(
            id=orm_obj.id,
            # ... field mappings
        )

    @staticmethod
    def to_orm(domain_obj: DomainEntity, orm_obj: Optional[ORMModel] = None) -> ORMModel:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMModel(...)
        # ... field mappings
        return orm_obj
```

### Required Domain Entity Analysis
Each mapper requires corresponding domain entities in `src/domain/entities/`. Missing domain entities must be created alongside mappers.

---

## 📝 Implementation Checklist Template

For each mapper implementation:
- [ ] Verify domain entity exists in `src/domain/entities/`
- [ ] Create domain entity if missing
- [ ] Implement `to_domain()` method with proper type conversion
- [ ] Implement `to_orm()` method with safe attribute handling
- [ ] Handle inheritance relationships (if applicable)
- [ ] Add type hints and documentation
- [ ] Create unit tests for bidirectional conversion
- [ ] Update this inventory document

**Next Steps**: Begin Phase 1 implementation with the 4 core financial asset mappers.