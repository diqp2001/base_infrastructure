# IBKR Contract Request — Verified Patterns

## The two-method contract pattern

Every IBKR asset repository implements **two contract methods**:

| Method | Used by | Purpose |
|--------|---------|---------|
| `_fetch_contract(symbol)` | `reqContractDetails` | Resolve the contract from IBKR — must NOT include fields that cause error 200 |
| `_fetch_historical_contract(symbol)` | `reqHistoricalData` | Fetch price history — must unambiguously identify one contract |

`ibkr_factor_value_repository._fetch_contract` dispatches to `_fetch_historical_contract` when the
repo has it, otherwise falls back to `_fetch_contract`:

```python
if hasattr(repo, '_fetch_historical_contract'):
    contract = repo._fetch_historical_contract(symbol)
else:
    contract = repo._fetch_contract(symbol)
```

### Adding a new asset repo

Always implement both methods. For non-FUT repos where the same spec works for both
API calls, `_fetch_historical_contract` can simply delegate:

```python
def _fetch_historical_contract(self, symbol: str) -> Optional[Contract]:
    return self._fetch_contract(symbol)
```

For FUT repos, use the **conId pattern** (see below).

---

## BondFuture / Rate Future (`IBKRBondFutureRepository`)

### `_fetch_contract` — for `reqContractDetails`

```python
contract.symbol       = local_symbol   # full local symbol, e.g. 'SR3N6'
contract.tradingClass = root            # last-2-chars stripped, e.g. 'SR3'
contract.secType      = "FUT"
contract.exchange     = "CME"          # CME for SOFR (SR3, SR1); CBOT for ZB/ZN/ZT
contract.includeExpired = True
# DO NOT set localSymbol
# DO NOT set lastTradeDateOrContractMonth
```

**Why:** setting either of those alongside `symbol` + `tradingClass` causes IBKR error 200
("No security definition found"). IBKR resolves uniquely from `symbol` + `tradingClass` + `exchange`.

### `_fetch_historical_contract` — for `reqHistoricalData`

Uses the **conId pattern**: calls `_fetch_contract_details` to resolve the 56-contract list,
finds the entry whose `local_symbol` matches, and returns a minimal contract with only `conId`
+ `exchange`. A conId-based contract is unambiguous regardless of symbol field semantics.

```python
def _fetch_historical_contract(self, symbol: str) -> Optional[Contract]:
    details_contract = self._fetch_contract(symbol)
    contract_details_list = self._fetch_contract_details(details_contract)
    detail = next(
        (c for c in contract_details_list if c.get('local_symbol') == symbol), None
    )
    con_id = detail.get('contract_id')
    contract = Contract()
    contract.conId = con_id
    contract.exchange = detail.get('exchange', 'CME')
    return contract
```

**Why conId:** `reqHistoricalData` for FUT cannot use the same field layout as
`reqContractDetails`. Setting `localSymbol` + `symbol` causes error 200; omitting
`localSymbol`/expiry causes error 321. Using conId bypasses both constraints.

---

## IndexFuture (`IBKRIndexFutureRepository`)

Same conId pattern as BondFuture — FUT contracts have the same IBKR ambiguity.

### `_fetch_contract` — for `reqContractDetails`

```python
contract.symbol       = local_symbol                         # e.g. 'ESZ6'
contract.tradingClass = _extract_underlying_symbol(symbol)   # e.g. 'ES'
contract.lastTradeDateOrContractMonth = build_future_contract_from_local_symbol(symbol)
contract.secType      = "FUT"
contract.exchange     = "CME"
contract.includeExpired = True
```

### `_fetch_historical_contract` — for `reqHistoricalData`

conId pattern (identical implementation to BondFuture, different print message).

---

## Root symbol extraction (FUT repos)

```python
root = local_symbol[:-2]   # 'SR3N6' → 'SR3', 'ZBZ6' → 'ZB', 'ESZ6' → 'ES'
```

Last 2 characters are always month-code letter + year digit. Strip positionally — do **not**
use `isalpha()`, which would wrongly include the month letter in the root for symbols like `SR3N6`.

---

## Non-FUT repos

For STK, BOND, CASH, CMDTY, IND — the same contract spec works for both API calls.
`_fetch_historical_contract` delegates to `_fetch_contract`:

| Repo | secType | Notes |
|------|---------|-------|
| `company_share_repository` | STK | symbol + SMART + USD |
| `equity_repository` | STK | symbol + SMART + USD |
| `share_repository` | STK | symbol + SMART + USD |
| `security_repository` | STK | symbol + SMART + USD |
| `bond_repository` | BOND | ISIN/CUSIP via secIdType |
| `commodity_repository` | FUT/CMDTY | expiry already in `_fetch_contract` |
| `currency_repository` | CASH | symbol + IDEALPRO |
| `index_repository` | IND | symbol + SMART |
