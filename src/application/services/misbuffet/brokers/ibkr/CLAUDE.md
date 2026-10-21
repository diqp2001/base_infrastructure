# IBKR Broker Layer

## Files

| File | Role |
|------|------|
| `IBTWSClient.py` | Low-level TWS API wrapper — connects, subscribes, receives callbacks |
| `interactive_brokers_broker.py` | High-level broker facade used by the engine |
| `contract_resolver.py` | Resolves domain symbols to IBKR `Contract` objects |

---

## Paper / live guard — one order path (BI-005)

| Check | Where | When |
|-------|-------|------|
| `IBKR_*` variables valid (all problems listed at once) | `ibkr_settings.validate_environment` | `resolve_endpoint`, i.e. `InteractiveBrokersBroker.__init__`, before connecting |
| `IBKR_ACCOUNT_MODE=live` needs `IBKR_ALLOW_LIVE=yes` | `ibkr_settings.account_mode` | same |
| logged-in account matches the mode (paper = `D…`, e.g. `DU1234567`) | `ibkr_settings.verify_connected_accounts` | every `IBTWSClient.place_order`, before an order id is used |

- Fail closed: no `managedAccounts` received, an `order.account` the login does not manage, or a
  multi-account login with no `order.account` → `AccountModeMismatch`, nothing sent; the broker
  (`_place_order_impl`) reports the order as not placed.
- `IBTWSClient.place_order` is the **only** `placeOrder` call in `src`
  (`tests/architecture/test_order_paths.py`). Other connections with a hard-coded `7497`
  (project trainers, `api_service/ibkr_service`, `broker_factory` defaults, monitoring) are
  data-only or go through this path — never add a second `placeOrder`.

---

## `format_ib_datetime` — end_date_time conversion rules

`get_historical_data` passes `end_date_time` through `format_ib_datetime` before sending
to TWS.  The function enforces two invariants:

| Input time component | Adjustment | Reason |
|----------------------|-----------|--------|
| Exactly midnight (`00:00:00`) | `+1 day` | IBKR treats a bare date as exclusive for daily bars — without the shift the last day is dropped |
| Any intraday time | `+1 second` | IBKR end boundary is exclusive for bar start times (`start >= end` is dropped) — without the shift the bar that starts exactly at `end_date_time` is never returned |

**Always pass a naive `datetime` representing the desired Eastern time.**  A UTC-aware
datetime bypasses the `ET → UTC` conversion inside `format_ib_datetime` and shifts the
window by 4–5 hours, dropping the intended bars.

```python
# Correct — naive, treated as US/Eastern, converted to UTC internally
end_dt = datetime(2026, 8, 6, 13, 35, 0)

# Wrong — already UTC (13:35 UTC = 09:35 ET), almost no data returned for that day
end_dt = datetime(2026, 8, 6, 13, 35, 0, tzinfo=timezone.utc)
```

**IBKR UTC wire format:** `yyyymmdd-hh:mm:ss` (dash separator, no `" UTC"` suffix).
Adding `" UTC"` produces TWS warning 10314 and is rejected.

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

---

## Historical request outcomes and the MIDPOINT permission finding (BI-037)

`InteractiveBrokersBroker.request_history(...)` performs ONE reqHistoricalData and returns a `HistoryResult`
(`history_result.py`): `complete` (bars + historicalDataEnd), `empty` (historicalDataEnd, zero bars), `failed`
(IBKR error for that request id, classified: `permission`, `pacing`, `no_data`, `no_security`, `invalid`,
`transient`, `other` — code and message kept verbatim), `timeout`, `not_sent`. `get_historical_data` returns bars
only for `complete`: bars received before an error or a timeout are discarded (never stored as a full answer).
Only `transient` / `pacing` / `timeout` are retried. IBKR notices (codes 2100–2199, 10167) no longer end a request.
A finished request's state is removed, so late callbacks for it are ignored.

**Diagnostic** (read-only, order methods blocked, client id 97 by default):

    python -m src.application.services.misbuffet.brokers.ibkr.history_diagnostics MSFT
    python -m src.application.services.misbuffet.brokers.ibkr.history_diagnostics SPY --types TRADES MIDPOINT --bar "8 hours"

**Finding 2026-10-21 (live account, TWS on 127.0.0.1:7497)** — qualified MSFT (conId 272093, primary NASDAQ) and
SPY (conId 756733, primary ARCA), same request path, durations 3 D, bars 1 day and 8 hours, useRTH True / False:
TRADES returns bars every time; MIDPOINT, BID and ASK are refused immediately with 162 "No market data permissions
for ISLAND STK" (MSFT) / "... for AMEX STK" (SPY) "Requested market data requires additional subscription for API".
The contract, exchange routing and parameters are identical between the passing and failing requests: the cause is
the account's missing US-equity QUOTE permission for the API session (trade history is available, quote history is
not). Fix outside the code: subscribe to the US equity quote bundle in Client Portal (Settings > Market Data
Subscriptions) and make sure it is shared with the API session. Until then the BI-036 reading order falls back to
the TRADES series for stocks. Option quotes (OPRA) are a separate subscription: SPX v2 option MIDPOINT bars worked.

**Availability finding 2026-10-21 (same diagnostic, `--sec-type OPT/FUT --end ...`)** — `SPY 281215C00775000`
(conId 844798243): every type (MIDPOINT, TRADES, BID_ASK) answers 162 "HMDS query returned no data" for windows ending
before 2026-08-24; MIDPOINT is served from 2026-08-24 on (10 bars per 5 days, 8h), TRADES only sparsely (2 bars in
the last 3 days: the option rarely trades). This is IBKR's history depth for the option, not a permission. SR3Z6 /
SR3U6 futures: MIDPOINT and TRADES complete for 3–6 Aug 2026. Consequence: the SPX v2 window 2026-08-05 → 08-30
has no option value before 24 Aug.
