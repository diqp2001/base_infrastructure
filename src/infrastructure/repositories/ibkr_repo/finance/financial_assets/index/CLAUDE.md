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

## IndexCompanyShare (`IBKRIndexCompanyShareRepository`)

Exchange map defaults to `CBOE`. Key mappings:
SPX → CBOE, NDX → NASDAQ, RUT → CBOE, DJI → NYSE, VIX → CBOE
