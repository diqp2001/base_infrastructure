# IBKR Index Contract Request — Verified Patterns

## IndexBond (`IBKRIndexBondRepository`)

### Verified contract spec — SOFR3

```
Symbol:        SOFR3
Security Type: Indexes (IND)
Currency:      USD
Exchange:      CME
```

```python
contract.symbol        = 'SOFR3'
contract.secType       = 'IND'
contract.exchange      = 'CME'
contract.primaryExchange = 'CME'
contract.currency      = 'USD'
# DO NOT set includeExpired — indices do not expire
# DO NOT set lastTradeDateOrContractMonth
```

### Exchange map (IBKRIndexBondRepository._get_index_exchange)

| Symbol | Exchange |
|--------|----------|
| SOFR3  | CME      |
| SOFR1  | CME      |
| USB    | CBOE     |
| TNX    | CBOE     |
| FVX    | CBOE     |
| IRX    | CBOE     |
| (default) | CME   |

### `reqHistoricalData` — CONFIRMED NOT AVAILABLE without paid subscription

`reqHistoricalData` for CME IND contracts (SOFR3, SOFR1) returns:

```
TWS Error 162: Historical Market Data Service error message:
No market data permissions for CME IND
```

**SMART exchange routing was tried and does NOT resolve this** — `exchange='SMART'`
with a resolved conId still returns Error 162. The permissions wall is at the
exchange data level, not the routing level.

**Root cause**: IBKR requires a paid CME Index market data subscription to receive
historical bars for IND-type contracts on CME. Without it, all `reqHistoricalData`
calls for SOFR3/SOFR1 fail regardless of contract spec or exchange field.

**Workaround**: Use the corresponding `BondFuture` contract instead (e.g. `SR3Z6`
for SOFR3). BondFuture contracts (FUT secType) do not require this subscription
and return full OHLCV history via `reqHistoricalData`.

Do **not** put `IndexBond` symbols (SOFR3, SOFR1) in the universe `factors` config
expecting OHLCV factor values — they will fail with Error 162.

---

## IndexCompanyShare (`IBKRIndexCompanyShareRepository`)

Exchange map defaults to `CBOE`. Key mappings:
SPX → CBOE, NDX → NASDAQ, RUT → CBOE, DJI → NYSE, VIX → CBOE
