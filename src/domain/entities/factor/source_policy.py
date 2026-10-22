"""
Market-data source selection policy (BI-026) — pure domain.

Which provider data type (SourceDataType: TRADES, MIDPOINT, BID, ASK, ...) to request for a field of an instrument,
given the INTENDED USE of the value, in order of preference, and whether falling back to the next one is allowed.

    policy.select("CompanyShareOption", group="price", field="close", use=IntendedUse.VALUATION_MARK)
      -> SourceChoice(order=(MIDPOINT, TRADES), fallback_allowed=True, rule=...)

Default policy (DEFAULT_SOURCE_POLICY):
  - price marks and model inputs: MIDPOINT first, then TRADES — trades do not happen on every bar (user rule,
    2026-10-20); a midpoint is a mark, never an execution price;
  - execution prices and trade statistics: TRADES only — a quote never stands in for a trade;
  - volume: TRADES only (midpoints have no volume);
  - implied / historical volatility (by subgroup): their own IBKR types;
  - any other raw field read as a mark: TRADES (IBKR's default type).
A combination no rule covers raises UnsupportedSourceSelection (never a silent default). A fallback is only taken
inside one rule, so it never changes the economic meaning the use asked for; the caller records which type
answered and why (ObservationProvenance.selection).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from src.domain.entities.factor.observation_quality import SourceDataType as D

ANY = "*"


class IntendedUse(str, Enum):
    VALUATION_MARK = "valuation_mark"        # mark-to-market, research marks
    MODEL_INPUT = "model_input"              # inputs of models / signals
    EXECUTION_PRICE = "execution_price"      # what a trade actually printed / filled at
    TRADE_STATISTICS = "trade_statistics"    # volume, trade counts
    YIELD = "yield"
    FINANCING = "financing"                  # rebate / fee rates


class UnsupportedSourceSelection(ValueError):
    """No rule of the policy covers this instrument / field / use."""


@dataclass(frozen=True)
class SourceRule:
    instrument_class: str                    # e.g. "CompanyShareOption", "Option" (suffix match) or ANY
    group: str                               # Factor group, e.g. "price", "volatility", or ANY
    field: str                               # factor name, e.g. "close", "volume", or ANY
    uses: Tuple[IntendedUse, ...]
    order: Tuple[D, ...]
    fallback_allowed: bool = False
    note: str = ""
    subgroup: str = ANY                      # Factor subgroup, e.g. "implied", or ANY

    def __post_init__(self):
        if not self.order:
            raise ValueError("a source rule needs at least one data type")
        if len(self.order) > 1 and not self.fallback_allowed:
            raise ValueError("several data types without fallback: state fallback_allowed explicitly")

    def matches(self, instrument_class: str, group: str, field: str, use: IntendedUse, subgroup: str = "") -> bool:
        return (use in self.uses
                and (self.subgroup == ANY or self.subgroup == subgroup)
                and (self.instrument_class == ANY or (instrument_class or "").endswith(self.instrument_class))
                and (self.group == ANY or self.group == group)
                and (self.field == ANY or self.field == (field or "").lower()))


@dataclass(frozen=True)
class SourceChoice:
    order: Tuple[D, ...]
    fallback_allowed: bool
    rule: SourceRule

    @property
    def preferred(self) -> D:
        return self.order[0]

    def selection_note(self, used: D, tried: Tuple[D, ...] = ()) -> str:
        """Why `used` was used: preferred, or the fallback taken and what was tried before."""
        if used == self.preferred:
            return f"{used.value}: preferred ({self.rule.note or 'policy'})"
        return (f"{used.value}: fallback after {', '.join(t.value for t in tried) or self.preferred.value} "
                f"returned no data ({self.rule.note or 'policy'})")


@dataclass(frozen=True)
class SourcePolicy:
    rules: Tuple[SourceRule, ...]
    version: str = "source-policy-v1"

    def select(self, instrument_class: str, group: Optional[str], field: Optional[str],
               use: IntendedUse = IntendedUse.VALUATION_MARK, subgroup: Optional[str] = None) -> SourceChoice:
        for rule in self.rules:                       # first matching rule wins: put specific rules first
            if rule.matches(instrument_class, group or "", field or "", use, subgroup or ""):
                return SourceChoice(rule.order, rule.fallback_allowed, rule)
        raise UnsupportedSourceSelection(
            f"no source rule for instrument {instrument_class!r}, group {group!r}, field {field!r}, use {use.value}")


_MARKS = (IntendedUse.VALUATION_MARK, IntendedUse.MODEL_INPUT)

DEFAULT_SOURCE_POLICY = SourcePolicy(rules=(
    SourceRule(ANY, ANY, "volume", _MARKS + (IntendedUse.TRADE_STATISTICS,), (D.TRADES,),
               note="volume exists for trades only"),
    SourceRule(ANY, "volatility", ANY, _MARKS, (D.OPTION_IMPLIED_VOLATILITY,), note="IBKR implied volatility",
               subgroup="implied"),
    SourceRule(ANY, "volatility", ANY, _MARKS, (D.HISTORICAL_VOLATILITY,), note="IBKR historical volatility",
               subgroup="historical"),
    # Shares: TRADES first — the owner's IBKR account has no US-equity quote permission, so MIDPOINT is refused
    # (162, BI-037); it stays in the list, tried after TRADES (2026-10-22, owner's choice). Options / futures keep
    # MIDPOINT first: their quotes are served (OPRA) and their trades are sparse.
    SourceRule("CompanyShare", "price", ANY, _MARKS, (D.TRADES, D.MIDPOINT), fallback_allowed=True,
               note="share mark: trades first (no equity quote permission), midpoint when no trade history"),
    SourceRule(ANY, "price", ANY, _MARKS, (D.MIDPOINT, D.TRADES), fallback_allowed=True,
               note="mark: midpoint first, trades when no quote history"),
    SourceRule(ANY, "price", ANY, (IntendedUse.EXECUTION_PRICE, IntendedUse.TRADE_STATISTICS), (D.TRADES,),
               note="executions are trades, never quotes"),
    SourceRule(ANY, ANY, ANY, _MARKS, (D.TRADES,), note="other raw fields: IBKR default type"),
))


# ── Raw IBKR series (BI-036) ────────────────────────────────────────────────────────────────────────────────────
# A raw IBKR factor is ONE series: name = the bar field (open / high / low / close / volume / barCount / wap),
# subgroup = the IBKR whatToShow it was requested with (TRADES, MIDPOINT, BID, ASK, BID_ASK, ...), frequency = the
# bar size. Ingestion stores exactly that type into that factor (never a fallback into the same series); the
# "MIDPOINT first, TRADES otherwise" choice is made when the series is READ (reading_order). Definitions created
# before this rule (subgroups 'ohlc', 'daily', ...) are legacy: read only when no whatToShow series has data.

WHAT_TO_SHOW = frozenset(d.value for d in D if d is not D.CALCULATED)
RAW_BAR_FIELDS = frozenset({"open", "high", "low", "close", "volume", "barCount", "wap"})
TRADES_ONLY_FIELDS = frozenset({"volume", "barCount", "wap"})          # IBKR returns -1 for quote types
# whatToShow series whose bars are NOT prices of the instrument (a close of OPTION_IMPLIED_VOLATILITY is a volatility):
# never read in place of a price — only when a dependency names that subgroup explicitly
NON_PRICE_WHAT_TO_SHOW = frozenset({D.OPTION_IMPLIED_VOLATILITY.value, D.HISTORICAL_VOLATILITY.value,
                                    D.REBATE_RATE.value, D.FEE_RATE.value, D.SCHEDULE.value})


def is_what_to_show(subgroup: Optional[str]) -> bool:
    return subgroup in WHAT_TO_SHOW


def is_raw_bar_field(name: Optional[str]) -> bool:
    return name in RAW_BAR_FIELDS


def exact_choice(subgroup: str) -> SourceChoice:
    """The factor's own series: its subgroup names the whatToShow; no fallback into it."""
    data_type = D(subgroup)
    return SourceChoice((data_type,), False, SourceRule(ANY, ANY, ANY, _MARKS, (data_type,),
                                                        note="the factor's own series (subgroup = whatToShow)"))


def reading_order(instrument_class: str, group: Optional[str], field: Optional[str],
                  use: IntendedUse = IntendedUse.VALUATION_MARK,
                  policy: "SourcePolicy" = DEFAULT_SOURCE_POLICY) -> Tuple[str, ...]:
    """whatToShow series to read for a raw field, in order of preference (e.g. close: MIDPOINT, TRADES)."""
    if field in TRADES_ONLY_FIELDS:
        return (D.TRADES.value,)
    return tuple(d.value for d in policy.select(instrument_class, group, field, use=use).order)


def validate_raw_definition(name: Optional[str], group: Optional[str], subgroup: Optional[str],
                            source: Optional[str]) -> None:
    """New raw IBKR definitions must name their series: subgroup in WHAT_TO_SHOW (volume-like fields: TRADES)."""
    if source != "ibkr" or not is_raw_bar_field(name):
        return
    if not is_what_to_show(subgroup):
        raise ValueError(f"raw IBKR factor {name!r} needs subgroup = an IBKR whatToShow "
                         f"({', '.join(sorted(WHAT_TO_SHOW))}), got {subgroup!r}")
    if name in TRADES_ONLY_FIELDS and subgroup != D.TRADES.value:
        raise ValueError(f"{name!r} exists only for TRADES bars (IBKR returns -1 for {subgroup})")
