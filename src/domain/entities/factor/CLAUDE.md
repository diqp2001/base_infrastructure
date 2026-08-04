factor structure and needs:
1. Domain entity in src.domain.entities.factor. with a calculate function if the factor value has dependencies
2. It's definition in factor library src.application.services.data.entities.factor.factor_library in the proper entity library
    2.1 it will be written if the factor has dependcies like this
    "return_open": {
        "class": IndexFuturePriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": IndexFutureFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": IndexFutureFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=4, hours=3, minutes=10)}
                },
                },
        "parameters": {}
    },
    if it has dependencies, it has a calculate function

3. It needs a mapper in src.infrastructure.repositories.mappers.factor with the following 
    IndexFuturePriceReturnFactorMapper, so add FactorMapper to Domain entity factor name class
    3.1  a  discriminator property
    in this example 
    IndexFuturePriceReturnFactorMapper
    is factor of financial_asset IndexFuture, so the discriminator is index_future
    @property
    def discriminator(self):
        return 'index_future'

    3.2 all the following function that should not need explanation
    @property
    def model_class(self):
        return IndexFuturePriceReturnFactorModel
    
    def get_factor_model(self):
        return IndexFuturePriceReturnFactorModel
    
    def get_factor_entity(self):
        return IndexFuturePriceReturnFactor
    
    def to_domain(self, orm_model: Optional[IndexFuturePriceReturnFactorModel]) -> Optional[IndexFuturePriceReturnFactor]:
        """Convert ORM model to IndexFuturePriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFuturePriceReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: IndexFuturePriceReturnFactor) -> IndexFuturePriceReturnFactorModel:
        """Convert IndexFuturePriceReturnFactor domain entity to ORM model."""
        return IndexFuturePriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )

4. it needs a factor model in src.infrastructure.models.factor.factor.py
    the class needs to look like this
    class IndexFuturePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_price_return_factor"
    }
5. it needs a local factor repository in src.infrastructure.repositories.local_repo.factor
    like IndexFuturePriceReturnFactorRepository
    5.1 the parent class needs to be BaseFactorRepository class IndexFuturePriceReturnFactorRepository(BaseFactorRepository, IndexFuturePriceReturnFactorPort): and IndexFuturePriceReturnFactorPort
    5.2 init function takes session and factory, with self.factory and self.mapper and self.mapper_value 
        def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = IndexFuturePriceReturnFactorMapper()
        self.mapper_value = FactorValueMapper()
    5.3  it needs the following property
        @property
        def entity_class(self):
            return self.get_factor_entity()
        @property
        def model_class(self):
            return self.mapper.model_class

    5.4 the _create_or_get function with the following structure

        def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """
        Get or create an index future price return factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                factor_type=kwargs.get('factor_type', 'index_future_price_return_factor')
            )
            if existing:
                return self._to_entity(existing)
            
            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                subgroup=kwargs.get('subgroup', 'daily'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'calculated'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
            )
            
            # Use FactorMapper to convert domain entity to ORM model
            # This ensures entity_type is properly set
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            #create_or_get dependencies
            if kwargs.get('dependencies'):
                dependencies = kwargs.get('dependencies')
                for dependency in dependencies.items():
                    entity_class = dependency[1].get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    
                    dependency_config = dependency[1]
                    dependency_entity = repo._create_or_get(
                            entity_class,
                            primary_key=dependency_config.get("name"),
                            group=dependency_config.get("group"),
                            subgroup=dependency_config.get("subgroup"),
                            frequency=dependency_config.get("frequency", "1d"),
                            data_type=dependency_config.get("data_type"),
                            factor_type=dependency_config.get("factor_type"),
                            source=dependency_config.get("source"),
                            definition=dependency_config.get("definition"),)


                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    repo_factor_dependency._create_or_get(independent_factor=dependency_entity, dependent_factor=self._to_entity(orm_factor), lag = dependency_config.get("parameters").get("lag"))
 
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create index future price return factor {primary_key}: {e}")
            return None
    5.5 get_by_all function with this structure
        def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: Optional[str] = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Retrieve a factor matching all provided (non-None) fields."""
        try:
            FactorModel = self.get_factor_model()

            query = self.session.query(FactorModel)

            # Mandatory filters
            query = query.filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )

            # Optional filters
            if factor_type is not None:
                query = query.filter(FactorModel.factor_type == factor_type)

            if subgroup is not None:
                query = query.filter(FactorModel.subgroup == subgroup)

            if frequency is not None:
                query = query.filter(FactorModel.frequency == frequency)

            if data_type is not None:
                query = query.filter(FactorModel.data_type == data_type)

            if source is not None:
                query = query.filter(FactorModel.source == source)

            return query.first()

        except Exception as e:
            print(f"Error retrieving index future price return factor by all attributes: {e}")
            return None
    5.6 and all these functions
           def get_by_id(self, id: int):
        entity = self._to_entity(self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none())
        return entity
    
    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()
    
    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)

    5.7 the repository needs to be added in the RepositoryFactory in src.infrastructure.repositories.repository_factory in the function

    create_local_repositories like this 'index_future_price_return_factor': IndexFuturePriceReturnFactorRepository(self.session, factory=self),

    and 

    a property like this :
     @property
    def index_future_price_return_factor_local_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_price_return_factor')
6.  it needs repository for IBKR IBKRIndexFuturePriceReturnFactorRepository 
class IBKRIndexFuturePriceReturnFactorRepository(BaseIBKRFactorRepository, IndexFuturePriceReturnFactorPort):
    6.1 init function needs to look like this
    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Index Future Price Return Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('index_future_price_return_factor')
    and  the parent class needs to be BaseFactorRepository IBKRIndexFuturePriceReturnFactorRepository(BaseIBKRFactorRepository, IndexFuturePriceReturnFactorPort) and IndexFuturePriceReturnFactorPort

    
    6.2  it needs the following property
        @property
        def entity_class(self):
            return self.local_repo.get_factor_entity()
        @property
        def model_class(self):
            return self.local_repo.get_factor_model()

    6.3 the _create_or_get function with the following structure

        def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an index future price return factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "return")
            subgroup: Factor subgroup (default: "daily")
            
        Returns:
            IndexFuturePriceReturnFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific return calculation data
            enhanced_kwargs = self._enhance_with_ibkr_return_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create index future price return factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for index future price return factor {name}: {e}")
            return None

        ***** very important the parameters of _create_or_get needs to look like this
        (self, name: str,**kwargs)


    6.4 it also needs all these functions

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[IndexFuturePriceReturnFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[IndexFuturePriceReturnFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_by_group(self, group: str) -> List[IndexFuturePriceReturnFactor]:
        """Get factors by group (delegates to local repo)."""
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str) -> List[IndexFuturePriceReturnFactor]:
        """Get factors by subgroup (delegates to local repo)."""
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self) -> List[IndexFuturePriceReturnFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False
    6.5 the repository needs to be added in the RepositoryFactory in src.infrastructure.repositories.repository_factory in the function

    create_ibkr_repositories like this 'index_future_price_return_factor': IBKRIndexFuturePriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
    and 

    a property like this :
     @property
    def index_future_price_return_factor_ibkr_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_price_return_factor')


7. it needs a FactorPort like IndexFuturePriceReturnFactorPort in src.domain.ports.factor

8. 
    all base factor of each domain entity needs to be added in ENTITY_FACTOR_MAPPING in src.infrastructure.repositories.mappers.factor.factor_mapper.py
    a base factor is a factor that doesn't have a calculate function, and is considered the main factor for a certain entity . IndexFactorEntity is the base factor for entity domain Index, while IndexPriceReturnFactor isn't

---

## Factor.GROUPS — canonical group keys

Valid group values (validated in `Factor.__init__`):

| Key | Typical use | Added |
|-----|-------------|-------|
| `price` | Market price data (OHLCV) | original |
| `return` | Price return / P&L | original |
| `holding` | Single holding metrics | original |
| `portfolio` | Aggregated portfolio metrics | original |
| `value` | Market value / portfolio value metrics (PortfolioValueFactor, CurrencyValueFactor, CompanyShareValueFactor, …) | 2026-07-29 |
| `momentum` | Momentum / trend signals | original |
| `technical` | Technical indicator signals | original |
| `volatility` | Risk / volatility metrics (use `subgroup="implied"` for implied vol; `"implied_volatility"` is NOT a group) | original |
| `volume` | Volume and turnover metrics | 2026-07-29 |
| `order` | Order-level factors | 2026-07-29 |
| `transaction` | Transaction-level factors | 2026-07-29 |
| `position` | Position-level factors | 2026-07-29 |
| `price_model` | Option pricing model outputs (BSM, Heston, CRR, …) | 2026-07-29 |
| `fundamental` | Fundamental financial data | original |
| `economic` | Macro-economic indicators | original |
| `risk` | Risk measures (VaR, CVaR…) | original |
| `valuation` | Valuation ratios and metrics | original |
| `greek` | Options / structured product Greeks | original |
| `liquidity` | Liquidity metrics | original |

**`"value"` was added 2026-07-29** — it was missing from the dict but widely used across value factors. Its absence caused `Invalid group 'value'` errors that silently broke `get_portfolio_value()` on every bar.

**`"volume"`, `"order"`, `"transaction"`, `"position"`, `"price_model"` were added 2026-07-29** to accommodate existing factor libraries that reference these groups (avg_turnover_6m, trading lifecycle factors, option pricing models).

**Do NOT add to `SOURCES`** — that dict is frozen. For a new data source use one of the existing canonical keys (`ibkr`, `calculated`, `fmp`, `yahoo`, `alpha_vantage`, `quandl`).

**`'option'` added 2026-07-31** — subgroup for the base `CompanyShareOptionFactor` OHLCV price points (close, open, high, low, volume for an option contract). This disambiguates them from share price factors that share the same `group='price'`.

## Factor.SUBGROUPS — new canonical keys (2026-07-29)

Added alongside the new groups above:

| Key | Typical group | Notes |
|-----|--------------|-------|
| `asset` | `value` | Asset-level value (CompanyShareValueFactor, CurrencyValueFactor) |
| `weekly` | `return` / `price` | Weekly frequency bars |
| `monthly` | `return` / `price` | Monthly frequency bars |
| `turnover` | `volume` | Average share turnover |
| `trend` | `volume` | Volume Price Trend |
| `range` | `price` | Price range (high − low) |
| `price` | `order` | Price subgroup in order context |
| `black_scholes` | `price_model` | BSM option pricing |
| `binomial_tree` | `price_model` | CRR binomial tree |
| `stochastic_volatility` | `price_model` | Heston model |
| `stochastic_rates` | `price_model` | Hull-White model |
| `sabr` | `price_model` | SABR model |
| `jump_diffusion` | `price_model` | Bates model |
| `local_volatility` | `price_model` | Dupire local vol |

---

## CompanyShareMidPriceFactor — special constraints

File: src/domain/entities/factor/finance/financial_assets/share_factor/company_share/company_share_mid_price_factor.py

This is a **leaf factor** (no `@property calculate_dependencies`) resolved by IBKR (Branch B).
Its `calculate()` signature differs from every other factor in the chain.

### calculate() signature
```python
def calculate(self, source_prices: List[Dict[str, Any]]) -> Optional[Decimal]:
```
Takes a list of price dicts, NOT a `dependencies: dict`. Each dict must contain:
- `'source'`: str (data provider name)
- `'price'`: Decimal
- `'timestamp'`: datetime
- `'group'`: str  — must equal `self.group` ('price')
- `'subgroup'`: str — must equal `self.subgroup` ('mid_price_true')

### min_sources constraint (line 69)
```python
if not source_prices or len(source_prices) < self.min_sources:
    return None
```
- `min_sources` default = **2**
- `outlier_threshold` default = **2.0** (modified Z-score cutoff)
- `_filter_same_group_subgroup` runs first: only prices with matching `group` + `subgroup` survive.
- After filtering, if fewer than `min_sources` prices remain → returns `None`.
- If exactly `min_sources` survive → average used. If more → median used (after outlier removal).
- `_remove_outliers` only activates when `len(prices) > 2`; with ≤2 prices no outlier removal occurs.

### Propagation of None
`None` from this factor propagates up as `Decimal('0')` at each consumer:
- `CompanyShareValueFactor.calculate()` coerces via `Decimal(str(raw or '0'))` → `0`
- `CompanySharePortfolioHoldingValueFactor.calculate()` → `price * quantity = 0`
- `CompanySharePortfolioValueFactor.calculate()` → sum of zeros = `0`
- `CompanySharePortfolioPortfolioHoldingValueFactor.calculate()` → `0`

If company share values are unexpectedly zero, check that IBKR is returning at least
`min_sources` price entries tagged with `group='price'` and `subgroup='mid_price_true'`.

---

## CompanyShareOptionMidPriceFactor — same rules as CompanyShareMidPriceFactor

File: `src/domain/entities/factor/finance/financial_assets/derivatives/option/company_share_option/company_share_option_mid_price_factor.py`

This is the option equivalent of `CompanyShareMidPriceFactor`. It obeys exactly the same
leaf factor rules:

### Fixes applied (2026-07-31)

| Field | Old (broken) | New (correct) | Rule |
|-------|-------------|---------------|------|
| `frequency` | `None` | `"1d"` | Rule 1 — `None` causes NULL DB INSERT |
| `source` | `"multiple"` | `"ibkr"` | Rule 2 — `"multiple"` not in `Factor.SOURCES` whitelist |

### ORM discriminator fix (2026-07-31)

`CompanyShareOptionModel.polymorphic_identity` was `"company_share_options"` (snake_case, plural)
but `CompanyShareOptionMapper.discriminator` is `"CompanyShareOption"` (PascalCase, singular).

**Fix**: Changed `polymorphic_identity` in
`src/infrastructure/models/finance/financial_assets/derivative/option/company_share_option.py`
to `"CompanyShareOption"` — consistent with the convention for all other polymorphic identities
in this codebase.

---

## CompanyShareOption universe support

When `CompanyShareOption: ["AAPL  281215C00260000"]` appears in the algorithm universe config,
`UnifiedPortfolioManager._ensure_asset_container(ticker, now)` is called. Since a
`CompanyShareOptionModel` is not a `CompanyShareModel`, the original code returned `None` and
the option was silently ignored.

### Fix (2026-07-31)

`_ensure_asset_container` now falls through to `_ensure_option_asset_container(ticker, now)`
when the `CompanyShareModel` query returns nothing:

```python
if not share:
    return self._ensure_option_asset_container(ticker, now)
```

`_ensure_option_asset_container` sets up the holding hierarchy for an option ticker:

1. **Resolve** `CompanyShareOptionModel` by `symbol` (OCC format, e.g. `"AAPL  281215C00260000"`)
   — the option **must already be in the DB** (fetched from IBKR during initialisation).
   If not found, logs a warning and returns `None`.

2. **Create/get** a `CompanyShareOptionPortfolio` sub-portfolio named `{main_portfolio_name}_CSO`
   (one per main portfolio, shared by all options).

3. **Create** `CompanyShareOptionPortfolioHolding` + `PositionModel` for the specific option
   (idempotent — skipped if holding already exists).

4. **Return** `sub_portfolio_id` for use as `portfolio_id` in `execute_trade`.

### Pre-requisite: option must be in the DB

The option resolution in step 1 queries the DB directly. The IBKR feed must have already
persisted the `CompanyShareOptionModel` row (via `IBKRCompanyShareOptionRepository`) before
the universe initialises its holdings. If the option is missing from the DB, the holding
is NOT created and the ticker is effectively excluded from the portfolio.

### Portfolio factory registration (2026-07-31)

`CompanyShareOptionPortfolioHoldingRepository` is now registered in `RepositoryFactory`:
```python
'CompanyShareOptionPortfolioHolding': CompanyShareOptionPortfolioHoldingRepository(self.session, factory=self),
```

### Additional fixes (2026-07-31)

**`Invalid subgroup 'option'` in `CompanyShareOptionFactorRepository._create_or_get`**

The default `subgroup='option'` was rejected by `Factor.__init__` because `'option'` was not in
`Factor.SUBGROUPS`. Fix: added `'option'` as a canonical subgroup in `factor.py` (typical group:
`price`). It identifies OHLCV price points belonging to an option contract as distinct from share
price factors in the same `price` group.

**`_create_or_get() got multiple values for argument 'entity_cls'` in batch creation**

`EntityService.create_or_get_batch_local` passes `entity_cls` as both a positional argument
and — when the factor library config dict contains an `'entity_cls'` or `'class'` key — as a
keyword argument in `**data`. Fix: pop both `'entity_cls'` and `'class'` from `data` before
calling `_create_or_get` in `src/application/services/data/entities/entity_service.py`.

### Additional fixes (2026-07-31 — second round)

**`CompanyShareOptionFactorRepository._create_or_get` invalid default group**

Default `group='company_share_option'` is NOT in `Factor.GROUPS`. Every call that relied on
the fallback default raised `ValueError: Invalid group 'company_share_option'` inside
`Factor.__init__`, causing `_create_or_get` to catch the exception and return `None`. The
result: no `CompanyShareOptionFactor` records were ever persisted to the DB.
Fix: changed default to `group='price'` (correct and in `Factor.GROUPS`). Applies to both
the existence-check `get_by_all(...)` call and the `domain_factor = get_factor_entity()(...)` call.

File: `src/infrastructure/repositories/local_repo/factor/finance/financial_assets/derivatives/option/company_share_option/company_share_option_factor_repository.py`

**`IBKRCompanyShareOptionFactorRepository._create_or_get` two bugs**

1. Calling convention: `self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)` omitted
   the required `entity_cls` first positional argument. Local repo signature is
   `_create_or_get(entity_cls, primary_key, **kwargs)`.
   Fix: `self.local_repo._create_or_get(CompanyShareOptionFactor, name, **enhanced_kwargs)`.

2. `source='ibkr_api'` in `_enhance_with_ibkr_option_data` is NOT in `Factor.SOURCES`.
   Fix: `source='ibkr'`.

File: `src/infrastructure/repositories/ibkr_repo/factor/finance/financial_assets/derivatives/option/company_share_option/ibkr_company_share_option_factor_repository.py`

**`CompanyShareOptionMidPriceFactor` routed to Branch B instead of Branch A**

`get_dependencies()` (plain method) is NOT detected by `hasattr(entity, 'calculate_dependencies')`
— so the resolution service routed this factor to Branch B (IBKR/direct fetch) instead of
Branch A (dependency chain). In a backtest, Branch B returns `None` for option prices, causing
option holding values to be incorrectly resolved via share-factor fallbacks.

Three changes applied:
1. `source='calculated'` (was `'ibkr'`): matches `CompanyShareMidPriceFactor`'s convention;
   also prevents self-inclusion in its own `DependencySpec source_not_in=["calculated"]` filter.
2. `calculate(self, dependencies: dict)` now accepts `{'CompanyShareOptionFactor': [list of floats]}`
   — same contract as `CompanyShareMidPriceFactor.calculate` — instead of the old `List[Dict]` format.
3. Replaced `get_dependencies()` with `@property calculate_dependencies` returning a `DependencySpec`
   querying `CompanyShareOptionFactor` with `group='price'` and `source_not_in=['calculated']`.

File: `src/domain/entities/factor/finance/financial_assets/derivatives/option/company_share_option/company_share_option_mid_price_factor.py`

### Regression tests

`src/tests/unit/test_factor_value_chain.py` now covers (22 tests total):
- `test_company_share_option_mid_price_factor_frequency_not_none` — `frequency='1d'` ✓
- `test_company_share_option_mid_price_factor_source_in_whitelist` — `source='calculated'` ✓
- `TestOptionMidPriceFactorResolution` class (5 tests):
  - `test_has_calculate_dependencies_property` — Branch A routing ✓
  - `test_calculate_dependencies_references_option_factor` — DependencySpec targets CompanyShareOptionFactor ✓
  - `test_calculate_returns_average_of_two_prices` — arithmetic ✓
  - `test_calculate_returns_none_when_insufficient_sources` — min_sources guard ✓
  - `test_calculate_wrong_key_returns_none` — share keys don't contaminate option resolution ✓

---

## CompanySharePortfolioPriceReturnFactor (added 2026-08-03)

File: `src/domain/entities/factor/finance/portfolio/company_share_portfolio_factor/company_share_portfolio_price_return_factor.py`

**Purpose**: Price return of a `CompanySharePortfolio` between two observations (start_price and end_price).

### Defaults
| Field | Value |
|-------|-------|
| `group` | `return` |
| `subgroup` | `daily` |
| `frequency` | `1d` |
| `data_type` | `numeric` |
| `source` | `calculated` |

### Resolution branch: A (has `calculate_dependencies`)
```python
@property
def calculate_dependencies(self) -> list:
    return ["CompanySharePortfolioFactor"]
```
Dependencies resolve two `CompanySharePortfolioFactor` records (close price) with different lags,
keyed as `"start_price"` and `"end_price"` in the factor library config.

### calculate() contract
```python
def calculate(self, dependencies: dict) -> Optional[Decimal]:
    start = dependencies.get("start_price")
    end   = dependencies.get("end_price")
    # returns (end - start) / start, or None if either is missing / start == 0
```

### ORM discriminator
`polymorphic_identity = "company_share_portfolio_price_return_factor"`

### Infrastructure layer artefacts
| Artefact | Path |
|----------|------|
| Mapper | `src/infrastructure/repositories/mappers/factor/company_share_portfolio_price_return_factor_mapper.py` |
| Port | `src/domain/ports/factor/finance/portfolio/company_share_portfolio_factor/company_share_portfolio_price_return_factor_port.py` |
| Local repo | `src/infrastructure/repositories/local_repo/factor/finance/portfolio/company_share_portfolio/company_share_portfolio_price_return_factor_repository.py` |
| ORM model | `src/infrastructure/models/factor/factor.py` — `CompanySharePortfolioPriceReturnFactorModel` |
| Factory key | `'CompanySharePortfolioPriceReturnFactor'` in `RepositoryFactory.create_local_repositories` |
| Factory property | `company_share_portfolio_price_return_factor_local_repo` |

### FactorMapper dispatch (factor_mapper.py)
```python
elif factor_type == 'company_share_portfolio_price_return_factor':
    return CompanySharePortfolioPriceReturnFactor(**base_args)
```

### Factor library entry
Library: `COMPANY_SHARE_PORTFOLIO_LIBRARY` in `src/application/services/data/entities/factor/factor_library/finance/portfolio/company_share_portfolio.py`

Key `"return_daily_3"`:
- two `CompanySharePortfolioFactor` deps keyed `"start_price"` (lag 5d) and `"end_price"` (lag 1d)

---

## CompanySharePortfolioEqualWeightReturnFactor (added 2026-08-03)

File: `src/domain/entities/factor/finance/portfolio/company_share_portfolio_factor/company_share_portfolio_equal_weight_return_factor.py`

**Purpose**: Equal-weight average of all component `CompanyShare` daily price returns over a period.
Unlike `CompanySharePortfolioPriceReturnFactor` (portfolio-level price ratio), this averages the
individual share returns — so each constituent contributes equally regardless of weight.

### Defaults
| Field | Value |
|-------|-------|
| `group` | `return` |
| `subgroup` | `daily` |
| `frequency` | `1d` |
| `data_type` | `numeric` |
| `source` | `calculated` |

### Resolution branch: A (has `calculate_dependencies`)
```python
@property
def calculate_dependencies(self) -> list:
    return ["CompanySharePriceReturnFactor"]
```
The resolution service collects a `CompanySharePriceReturnFactor` value for **each** component
share in the portfolio and delivers them as a list under key `"CompanySharePriceReturnFactor"`.

### calculate() contract
```python
def calculate(self, dependencies: dict) -> Optional[Decimal]:
    raw = dependencies.get("CompanySharePriceReturnFactor")
    # raw can be a scalar (single share) or list (multiple shares)
    # filters out None, averages the rest; returns None if no valid values
```

### ORM discriminator
`polymorphic_identity = "company_share_portfolio_equal_weight_return_factor"`

### Infrastructure layer artefacts
| Artefact | Path |
|----------|------|
| Mapper | `src/infrastructure/repositories/mappers/factor/company_share_portfolio_equal_weight_return_factor_mapper.py` |
| Port | `src/domain/ports/factor/finance/portfolio/company_share_portfolio_factor/company_share_portfolio_equal_weight_return_factor_port.py` |
| Local repo | `src/infrastructure/repositories/local_repo/factor/finance/portfolio/company_share_portfolio/company_share_portfolio_equal_weight_return_factor_repository.py` |
| ORM model | `src/infrastructure/models/factor/factor.py` — `CompanySharePortfolioEqualWeightReturnFactorModel` |
| Factory key | `'CompanySharePortfolioEqualWeightReturnFactor'` in `RepositoryFactory.create_local_repositories` |
| Factory property | `company_share_portfolio_equal_weight_return_factor_local_repo` |

### FactorMapper dispatch (factor_mapper.py)
```python
elif factor_type == 'company_share_portfolio_equal_weight_return_factor':
    return CompanySharePortfolioEqualWeightReturnFactor(**base_args)
```

### Factor library entry
Library: `COMPANY_SHARE_PORTFOLIO_LIBRARY` in `src/application/services/data/entities/factor/factor_library/finance/portfolio/company_share_portfolio.py`

Key `"return_eq_w_daily_3"`:
- one `CompanySharePriceReturnFactor` dep keyed `"CompanySharePriceReturnFactor"` (lag 5d)






