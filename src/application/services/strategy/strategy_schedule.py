"""
A strategy's two schedules as category + count (Frequency): how often it TRADES and how often it RETRAINS.

Each project states its schedule with its own config keys; this module reads which ones the strategy carries and
offers only the categories the project can run:

trading   trading.config_interval.custom_interval_minutes   intraday projects        minutes / hours
          trading.config_interval.custom_interval_days      daily-step projects      days / weeks (the engine skips
                                                                                     non-trading days)
          '<...>.rebalance_every' next to                   rebalancing projects     days / weeks / months: the
          '<...>.retrain_every_rebalances'                  (deciles)                decile cycle re-forms at each
                                                                                     period end (stm_decile_cycle);
                                                                                     absent = every month
training  retrain_every_days (typed field)                  calendar days            days / weeks / months (a month
                                                                                     = 30 days)
          '<...>.retrain_every_rebalances'                  every N rebalances       the trading category or a longer
                                                                                     one, in whole rebalances (a week
                                                                                     = 5 trading days, a month = 21)

horizon   prediction_horizon (typed, in model ROWS)            a row = one rebalance period (rebalancing projects)
                                                                 or one data bar (bar_frequency): the horizon is
                                                                 picked as category + count and stored as rows

``schedule(strategy)`` describes the three for the designer; ``schedule_changes(strategy, trading, training)`` gives the
section / typed-field updates that store them.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from src.domain.entities.strategy.frequency import COUNT_CHOICES, UNIT_LABELS, Frequency

REBALANCES_KEY = "retrain_every_rebalances"
REBALANCE_EVERY_KEY = "rebalance_every"
REBALANCE_UNITS = ("days", "weeks", "months")
TRADING_DAYS = {"days": 1, "weeks": 5, "months": 21}         # to count whole rebalances in a training interval
ALL_UNITS = ("minutes", "hours", "days", "weeks", "months")
TRADING_MINUTES = {"minutes": 1, "hours": 60, "days": 390, "weeks": 5 * 390, "months": 21 * 390}


def _find_key(sections: Dict[str, Any], key: str) -> Optional[Tuple[str, List[str]]]:
    """(section name, path inside it) of the first ``key`` found in the sections (dicts only)."""
    def walk(node, path):
        if isinstance(node, dict):
            if key in node:
                return path + [key]
            for k, v in node.items():
                found = walk(v, path + [k])
                if found:
                    return found
        return None

    for name, content in (sections or {}).items():
        found = walk(content, [])
        if found:
            return name, found
    return None


def _get(node, path):
    for p in path:
        node = node[p]
    return node


def _slot(units: Tuple[str, ...], current: Optional[Frequency], fixed: bool = False, note: str = "",
          stored_in: str = "") -> Dict[str, Any]:
    counts = {}
    for unit in units:
        choices = list(COUNT_CHOICES[unit])
        if current is not None and current.unit == unit and current.count not in choices:
            choices = sorted(choices + [current.count])
        counts[unit] = choices
    return {"units": [(u, UNIT_LABELS[u]) for u in units], "counts": counts, "current": current, "fixed": fixed,
            "note": note, "stored_in": stored_in, "editable": bool(units) and not fixed, "follows": None,
            "floor": None}


def _interval(strategy) -> Dict[str, Any]:
    return dict(strategy.section("trading").get("config_interval") or {})


def _rebalance(strategy) -> Optional[Tuple[str, List[str], Frequency]]:
    """(section, path of the rebalancing dict, rebalance frequency) of a rebalancing project, else None."""
    found = _find_key(strategy.sections, REBALANCES_KEY)
    if not found:
        return None
    section, path = found
    parent = _get(strategy.section(section), path[:-1])
    return section, path[:-1], Frequency.parse(parent.get(REBALANCE_EVERY_KEY) or "1mo") or Frequency("months", 1)


def trading_schedule(strategy) -> Dict[str, Any]:
    rebalance = _rebalance(strategy)
    if rebalance:
        section, path, current = rebalance
        return _slot(REBALANCE_UNITS, current,
                     note="the deciles are re-formed at the end of each period (one model row per period-end close; "
                          "the annualisation follows the period)",
                     stored_in=".".join([section, *path, REBALANCE_EVERY_KEY]))
    interval = _interval(strategy)
    if interval.get("custom_interval_minutes"):
        return _slot(("minutes", "hours"), Frequency.from_minutes(int(interval["custom_interval_minutes"])),
                     note="a trading decision at this interval within the session",
                     stored_in="trading.config_interval.custom_interval_minutes")
    if interval.get("custom_interval_days"):
        days = int(interval["custom_interval_days"])
        current = Frequency("weeks", days // 7) if days >= 7 and days % 7 == 0 else Frequency("days", days)
        return _slot(("days", "weeks"), current,
                     note="one engine step per interval (non-trading days are skipped)",
                     stored_in="trading.config_interval.custom_interval_days")
    return _slot((), None, note="this project's trading schedule is not a setting (it follows its data bars)")


def training_schedule(strategy) -> Dict[str, Any]:
    rebalance = _rebalance(strategy)
    if rebalance:
        section, path, trade = rebalance
        n = int(_get(strategy.section(section), path).get(REBALANCES_KEY) or 1)
        slot = _slot(REBALANCE_UNITS, Frequency(trade.unit, trade.count * n),
                     note="retrains every N rebalances, never more often than it trades (a week = 5 trading days, "
                          "a month = 21)",
                     stored_in=".".join([section, *path, REBALANCES_KEY]))
        slot["follows"] = "trading"                 # the page greys out categories more frequent than trading
        return slot
    if strategy.retrain_every_days is not None:
        return _slot(("days", "weeks", "months"), Frequency.from_days(int(strategy.retrain_every_days)),
                     note="calendar days between retrainings (a month counts 30 days)",
                     stored_in="retrain_every_days")
    return _slot((), None, note="this project does not retrain on a schedule")


def row_frequency(strategy, trading: Optional[Frequency] = None) -> Optional[Frequency]:
    """What one model row stands for: the rebalance period of a rebalancing project (``trading`` when it is being
    changed), else the data bar (bar_frequency / bar_size); None when unknown."""
    rebalance = _rebalance(strategy)
    if rebalance:
        return trading or rebalance[2]
    from src.application.services.strategy.strategy_definition import bar_frequency
    return Frequency.parse(strategy.bar_frequency) or Frequency.parse(bar_frequency(strategy.bar_size) or "")


def horizon_rows(row: Frequency, horizon: Frequency) -> int:
    """Rows in a horizon (trading time: a day = 390 minutes, a week 5 days, a month 21 days), at least 1."""
    return max(1, round(TRADING_MINUTES[horizon.unit] * horizon.count / (TRADING_MINUTES[row.unit] * row.count)))


def horizon_schedule(strategy) -> Dict[str, Any]:
    row = row_frequency(strategy)
    if row is None:
        return _slot((), None, note="the rows of this project's data are not known: the horizon stays in rows")
    rows = strategy.prediction_horizon if strategy.prediction_horizon is not None else 1
    slot = _slot(ALL_UNITS, Frequency(row.unit, row.count * int(rows)),
                 note=f"how far ahead the model predicts; one row = {row.label.replace('every ', 'one ')} "
                      f"(stored as {rows} row{'s' if rows != 1 else ''})", stored_in="prediction_horizon")
    slot["follows"] = "trading" if _rebalance(strategy) else None
    slot["floor"] = row.unit                 # never shorter than one row
    return slot


def schedule(strategy) -> Dict[str, Dict[str, Any]]:
    return {"trading": trading_schedule(strategy), "training": training_schedule(strategy),
            "horizon": horizon_schedule(strategy)}


def rebalances_between(trade: Frequency, training: Frequency) -> int:
    """Whole rebalances in one training interval (at least 1): every 2 weeks with weekly trading -> 2."""
    return max(1, round(TRADING_DAYS[training.unit] * training.count / (TRADING_DAYS[trade.unit] * trade.count)))


def _check(slot: Dict[str, Any], frequency: Frequency, what: str) -> None:
    units = [u for u, _ in slot["units"]]
    if slot["fixed"]:
        if frequency != slot["current"]:
            raise ValueError(f"{what} is fixed for this project: {slot['note']}")
        return
    if frequency.unit not in units:
        allowed = ", ".join(UNIT_LABELS[u] for u in units) or "none"
        raise ValueError(f"{what}: this project cannot run {frequency.label} (categories it can run: {allowed})")


def schedule_changes(strategy, trading: Optional[Frequency] = None, training: Optional[Frequency] = None,
                     horizon: Optional[Frequency] = None
                     ) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Dict[str, Any]]:
    """(sections to update or None, typed fields to update) storing the schedules; ValueError when the project
    cannot run one of them."""
    sections, typed = _schedule_changes(strategy, trading, training)
    if horizon is not None:
        row = row_frequency(strategy, trading)
        if row is None:
            raise ValueError("Prediction horizon: this project's rows are not known; it stays in rows")
        if ALL_UNITS.index(horizon.unit) < ALL_UNITS.index(row.unit):
            raise ValueError(f"Prediction horizon: {horizon.label.replace('every ', '')} is shorter than one row "
                             f"({row.label.replace('every ', '')})")
        typed["prediction_horizon"] = horizon_rows(row, horizon)
    return sections, typed


def _schedule_changes(strategy, trading: Optional[Frequency] = None, training: Optional[Frequency] = None
                      ) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Dict[str, Any]]:
    sections: Dict[str, Dict[str, Any]] = {}
    typed: Dict[str, Any] = {}
    rebalance = _rebalance(strategy)
    if rebalance:                                       # rebalancing project: both live in its rebalancing dict
        section, path, trade = rebalance
        if trading is not None:
            _check(trading_schedule(strategy), trading, "Trading frequency")
            trade = trading
        content = copy.deepcopy(strategy.section(section))
        parent = _get(content, path)
        parent[REBALANCE_EVERY_KEY] = trade.token
        if training is not None:
            if training.unit not in REBALANCE_UNITS[REBALANCE_UNITS.index(trade.unit):]:
                raise ValueError(f"Training frequency: retraining {training.label} is more often than trading "
                                 f"{trade.label}; pick {trade.label} or longer")
            parent[REBALANCES_KEY] = rebalances_between(trade, training)
        return {section: content}, {}
    if trading is not None:
        slot = trading_schedule(strategy)
        _check(slot, trading, "Trading frequency")
        if not slot["fixed"]:
            interval = _interval(strategy)
            if "custom_interval_minutes" in interval:
                interval["custom_interval_minutes"] = trading.minutes
            else:
                interval["custom_interval_days"] = trading.days
            sections["trading"] = {**strategy.section("trading"), "config_interval": interval}
    if training is not None:
        _check(training_schedule(strategy), training, "Training frequency")
        typed["retrain_every_days"] = training.days
    return (sections or None), typed
