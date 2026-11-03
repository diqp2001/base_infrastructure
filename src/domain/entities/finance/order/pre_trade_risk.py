"""
Pre-trade risk limits (BI-022): the checks every order must pass before it is sent to a broker. Pure rules —
the gate that feeds them account / price snapshots lives in the broker layer (PreTradeGate).

A limit left at None is not checked. Quantities are signed (buy > 0, sell < 0); positions are in units of the
instrument, notionals in account currency (price × |quantity| × multiplier).

  max_order_quantity     |order quantity|
  max_order_notional     |order notional|
  max_position_quantity  |position after the order|
  max_gross_exposure     gross exposure after the order (sum of |position notional|)
  max_net_exposure       |net exposure| after the order (sum of signed position notionals)       (P.05)
  max_concentration      |position notional after the order| / net liquidation value (0.2 = 20 %) (P.05)
                         gross / net / concentration refuse only an order that INCREASES the measure: above a limit
                         (prices moved, limit lowered) an order that reduces it is always allowed (P.07.08)
  require_buying_power   an order that increases |position| must fit the broker's buying power   (P.05)
  max_quote_age_seconds  the price used to judge the order must be this fresh — no price, or an older one,
                         refuses the order (stale market data never sizes an order)
  require_cash           a buy's notional must not exceed available cash
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.domain.entities.factor.observation_quality import ValidationResult


@dataclass(frozen=True)
class RiskLimits:
    max_order_quantity: Optional[float] = None
    max_order_notional: Optional[float] = None
    max_position_quantity: Optional[float] = None
    max_gross_exposure: Optional[float] = None
    max_quote_age_seconds: Optional[float] = 60.0
    require_cash: bool = True
    max_net_exposure: Optional[float] = None
    max_concentration: Optional[float] = None
    require_buying_power: bool = False


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    quantity: float                       # signed: buy > 0, sell < 0
    multiplier: float = 1.0


@dataclass(frozen=True)
class PriceSnapshot:
    price: Optional[float]
    as_of: Optional[datetime]
    unusable_reason: Optional[str] = None      # why the market data may not size an order (delayed, stale ...)


@dataclass(frozen=True)
class AccountSnapshot:
    cash: float
    positions: Dict[str, float] = field(default_factory=dict)          # symbol -> signed quantity
    gross_exposure: float = 0.0                                         # sum of |position notional| now
    net_exposure: float = 0.0                                           # sum of signed position notionals now
    net_liquidation: Optional[float] = None                             # account value (concentration)
    buying_power: Optional[float] = None                                # broker buying power (margin)


def check_order(intent: OrderIntent, price: Optional[PriceSnapshot], account: AccountSnapshot, limits: RiskLimits,
                now: datetime) -> List[ValidationResult]:
    """Every configured limit as a ValidationResult; the order may be sent only when all passed."""
    results: List[ValidationResult] = []

    def check(rule: str, ok: bool, reason: str) -> None:
        results.append(ValidationResult(rule, ok, "" if ok else reason))

    qty = float(intent.quantity)
    check("quantity_nonzero", qty != 0 and math.isfinite(qty), f"order quantity {intent.quantity!r}")
    if limits.max_order_quantity is not None:
        check("max_order_quantity", abs(qty) <= limits.max_order_quantity,
              f"|{qty}| > max order quantity {limits.max_order_quantity}")
    position_after = account.positions.get(intent.symbol, 0.0) + qty
    if limits.max_position_quantity is not None:
        check("max_position_quantity", abs(position_after) <= limits.max_position_quantity,
              f"position after order {position_after} exceeds {limits.max_position_quantity}")

    needs_price = (limits.max_order_notional is not None or limits.max_gross_exposure is not None
                   or limits.require_cash or limits.max_quote_age_seconds is not None
                   or limits.max_net_exposure is not None or limits.max_concentration is not None
                   or limits.require_buying_power)
    if not needs_price:
        return results
    usable = (price is not None and price.unusable_reason is None and price.price is not None
              and math.isfinite(price.price) and price.price > 0)
    check("price_available", usable, f"no usable price for {intent.symbol}"
          + (f" ({price.unusable_reason})" if price is not None and price.unusable_reason else ""))
    if not usable:
        return results
    if limits.max_quote_age_seconds is not None:
        age = None if price.as_of is None else (now - price.as_of).total_seconds()
        check("fresh_price", age is not None and 0 <= age <= limits.max_quote_age_seconds,
              f"price of {intent.symbol} is {'undated' if age is None else f'{age:.0f}s old'} "
              f"(max {limits.max_quote_age_seconds:.0f}s)")
    notional = abs(qty) * price.price * intent.multiplier
    if limits.max_order_notional is not None:
        check("max_order_notional", notional <= limits.max_order_notional,
              f"order notional {notional:.2f} > {limits.max_order_notional}")
    if limits.max_gross_exposure is not None:
        before = abs(account.positions.get(intent.symbol, 0.0)) * price.price * intent.multiplier
        after = account.gross_exposure - before + abs(position_after) * price.price * intent.multiplier
        check("max_gross_exposure", after <= limits.max_gross_exposure or after < account.gross_exposure,
              f"gross exposure after order {after:.2f} > {limits.max_gross_exposure}")
    if limits.require_cash and qty > 0:
        check("cash_available", notional <= account.cash, f"buy notional {notional:.2f} > cash {account.cash:.2f}")
    unit = price.price * intent.multiplier
    position_before = account.positions.get(intent.symbol, 0.0)
    if limits.max_net_exposure is not None:
        net_after = account.net_exposure + qty * unit
        check("max_net_exposure", abs(net_after) <= limits.max_net_exposure
              or abs(net_after) < abs(account.net_exposure),
              f"|net exposure after order| {abs(net_after):.2f} > {limits.max_net_exposure}")
    if limits.max_concentration is not None:
        nlv = account.net_liquidation
        ok = nlv is not None and nlv > 0 and (abs(position_after) * unit <= limits.max_concentration * nlv
                                              or abs(position_after) < abs(position_before))
        check("max_concentration", ok, "no net liquidation value" if not nlv or nlv <= 0 else
              f"{intent.symbol} after order {abs(position_after) * unit:.2f} > {limits.max_concentration:.0%} "
              f"of {nlv:.2f}")
    if limits.require_buying_power and abs(position_after) > abs(position_before):
        added = (abs(position_after) - abs(position_before)) * unit
        bp = account.buying_power
        check("buying_power", bp is not None and added <= bp,
              "no buying power from the broker" if bp is None else f"added exposure {added:.2f} > buying power "
                                                                   f"{bp:.2f}")
    return results
