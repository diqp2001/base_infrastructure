# IBKR Broker Layer

## Files

| File | Role |
|------|------|
| `IBTWSClient.py` | Low-level TWS API wrapper — connects, subscribes, receives callbacks |
| `interactive_brokers_broker.py` | High-level broker facade used by the engine |
| `contract_resolver.py` | Resolves domain symbols to IBKR `Contract` objects |

---

## whatToShow Routing — (group, subgroup) Convention

`OPTION_IMPLIED_VOLATILITY` must only be sent to IBKR when the factor actually represents
implied volatility. All other factors should use `TRADES` (or their own specific type).

The routing is driven by the factor's `(group, subgroup)` pair — **not** by factor name:

| `group` | `subgroup` | IBKR `whatToShow` |
|---------|-----------|-------------------|
| `"volatility"` | `"implied"` | `OPTION_IMPLIED_VOLATILITY` |
| `"volatility"` | `"historical"` | `HISTORICAL_VOLATILITY` |
| anything else | anything else | `TRADES` |

This table is implemented in **two places that must stay in sync**:

- [`ibkr_factor_value_repository.py`](../../../../../infrastructure/repositories/ibkr_repo/factor/ibkr_factor_value_repository.py) — `_GROUP_SUBGROUP_TO_WHAT_TO_SHOW` class dict + `_resolve_what_to_show_from_group(group, subgroup)`
- [`market_data_history_service.py`](../../data/market_data_history_service.py) — `_GROUP_SUBGROUP_TO_WHAT_TO_SHOW` class dict + `_resolve_what_to_show_for_factor(factor)`

The factor library entry for implied volatility must declare:
```python
"group": "volatility",
"subgroup": "implied",
```

The factor grouping key in `_group_factors_by_symbol_factor_group_and_frequency` includes
`subgroup` so that factors with the same group but different subgroups are batched into
separate IBKR requests with the correct `whatToShow`.

To add a new volatility-type factor: add one row to both dicts above.

---

## Known IBKR Data Availability Constraints

### Error 162 — No historical market data

**TWS error message:**
```
TWS Error 162: Historical Market Data Service error message:
No historical market data for AAPL/OPT@IBVOL OptionImpliedVol 300
```

**Conditions that produce this error (all three must hold):**
1. Requesting **option implied volatility** (`whatToShow = "OPTION_IMPLIED_VOLATILITY"` / `@IBVOL`)
   **directly on a `secType="OPT"` contract** (i.e. the option contract itself, not the underlying share)
2. **No active IBKR market data subscription** covering that option chain
3. **No trades have been made** on that option during the requested window
   — IBKR only retains free implied-vol history when there has been trade activity

**Typical trigger:** requesting IV history on an option that is fewer than ~5 days from
expiration when no subscription is held and the option has seen little or no trade volume.

**Important exception — querying IV via the underlying company share:**
Requesting `what_to_show = "OPTION_IMPLIED_VOLATILITY"` on a **`secType="STK"` contract**
(i.e. the underlying company share, not an option contract) **works reliably even within
5 days of expiration and without a subscription.** IBKR serves this data from the share's
own historical data feed, which has broader free-tier coverage.

Use this approach to get IV when close to expiry:
```python
# Works < 5 DTE, no subscription needed
contract = Contract()
contract.symbol = "AAPL"
contract.secType = "STK"
contract.exchange = "SMART"
contract.currency = "USD"
bars = ib.reqHistoricalData(contract, ..., whatToShow="OPTION_IMPLIED_VOLATILITY")
```

**Free lookback window:** confirmed ~74 days back from today without a subscription.
As of 2026-08-03, `end_date_time = "20260520-13:30:00"` succeeds — data from
roughly 2.5 months ago is freely available via the share contract.
When building backtest date ranges for IV, cap `end_date_time` to no earlier than
~70 days in the past to stay safely within the free tier.

See also: [ibkr_instrument_factor_repository.py:217](../../../../../infrastructure/repositories/ibkr_repo/factor/ibkr_instrument_factor_repository.py)

**How to handle in code:**
- Treat error 162 for `@IBVOL` requests as a soft miss — log at `WARNING` and continue;
  do not treat it as a fatal error or retry it in a tight loop.
- Fall back to deriving an approximate mid-price from bid/ask if available.
- If IV is required for valuation, gate the request on subscription availability before
  calling `reqHistoricalData`.

**Example guard pattern:**
```python
if not self.ibkr_client.has_market_data_subscription(contract):
    logger.warning(
        "Skipping IBVOL request for %s — no subscription and no guaranteed trade history",
        contract.localSymbol,
    )
    return None
```

---

### Error 162 — No historical option price data (company share options, near expiry)

**Conditions that produce this error (all three must hold):**
1. Requesting **option TRADES / MIDPOINT / BID_ASK price history** for a company share option
2. **No active IBKR market data subscription** covering that option chain
3. The option is **fewer than ~5 days from expiration**
   — IBKR does not retain free price history for very near-expiry options without a subscription,
   regardless of whether any trades occurred

**Key difference from the IBVOL case:** this applies to regular price bars (`TRADES`, `MIDPOINT`,
`BID_ASK`), not just implied volatility. Without a subscription the data simply does not exist
for near-expiry company share options.

**How to handle in code:**
- Check days-to-expiry before requesting; skip or substitute if `dte < 5` and no subscription.
- Use the same soft-miss pattern: log at `WARNING`, return `None`, do not retry.
- For backtesting, mark those dates as unavailable rather than treating them as zero price.

**Example guard pattern:**
```python
days_to_expiry = (contract_expiry_date - date.today()).days
if days_to_expiry < 5 and not self.ibkr_client.has_market_data_subscription(contract):
    logger.warning(
        "Skipping price history for %s — %d DTE with no subscription",
        contract.localSymbol,
        days_to_expiry,
    )
    return None
```
