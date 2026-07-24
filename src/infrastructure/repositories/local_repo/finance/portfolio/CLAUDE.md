# Portfolio Repository — Conventions

## Portfolio type hierarchy and holding naming

| Portfolio domain class     | Can contain holding types ending with… |
|---------------------------|----------------------------------------|
| `CurrencyPortfolio`       | `CurrencyPortfolioHolding`             |
| `CompanySharePortfolio`   | `CompanySharePortfolioHolding`         |
| `Portfolio` (base)        | `*PortfolioPortfolioHolding`           |

### Key rule
A **base `Portfolio`** can hold other sub-portfolios. Each sub-portfolio holding type
follows the pattern `<AssetType>PortfolioPortfolioHolding`, e.g.:
- `CurrencyPortfolioPortfolioHolding`   — a CurrencyPortfolio held inside a Portfolio
- `CompanySharePortfolioPortfolioHolding` — a CompanySharePortfolio held inside a Portfolio

The double `Portfolio` suffix distinguishes "portfolio held inside a portfolio" from a
leaf-asset holding.

## `get_related_entities` contract per repo

| Repository                              | `get_related_entities(id)` returns                        |
|-----------------------------------------|-----------------------------------------------------------|
| `PortfolioRepository`                   | All sub-portfolio holding domain entities in that portfolio (dynamic dispatch via `holding_type`) |
| `CurrencyPortfolioRepository`           | All `CurrencyPortfolioHolding` domain entities            |
| `CompanySharePortfolioRepository`       | All `CompanySharePortfolioHolding` domain entities        |
| `CurrencyPortfolioPortfolioHoldingRepository` | The `CurrencyPortfolioModel` asset the holding points to  |
| `CompanySharePortfolioPortfolioHoldingRepository` | The `CompanySharePortfolioModel` asset the holding points to |

## Dynamic dispatch in `PortfolioRepository.get_related_entities`

Queries `HoldingModel` by `container_id = portfolio_id`, then for each holding:
1. Reads `holding_type` (the ORM discriminator column).
2. Skips any holding whose type does NOT contain `'PortfolioPortfolioHolding'`
   (those are leaf-asset holdings, not sub-portfolio holdings).
3. Strips the trailing `'s'` from the `holding_type` discriminator to get the factory key
   (e.g. `"CurrencyPortfolioPortfolioHoldings"` → `"CurrencyPortfolioPortfolioHolding"`).
4. Calls `factory.get_local_repository(repo_key).get_by_id(holding.id)` to get the
   typed domain entity.
