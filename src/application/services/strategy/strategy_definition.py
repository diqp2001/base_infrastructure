"""
The typed definition of a Strategy read from a project's native config dict (bar size / frequency, model type,
training window, retraining, prediction horizon). A leaf module: the adapters, the project registration and the
design service all read it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

_BAR_UNITS = {"sec": "s", "secs": "s", "min": "m", "mins": "m", "hour": "h", "hours": "h", "day": "d",
              "days": "d", "week": "w", "weeks": "w", "month": "mo", "months": "mo"}


def bar_frequency(bar_size: Optional[str], bar_minutes: Optional[int] = None) -> Optional[str]:
    """'10 mins' -> '10m', '1 day' -> '1d' (bar_minutes, when the project states it, wins)."""
    if bar_minutes:
        return f"{int(bar_minutes)}m"
    parts = (bar_size or "").split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].lower() in _BAR_UNITS:
        return f"{int(parts[0])}{_BAR_UNITS[parts[1].lower()]}"
    return None


def strategy_definition(native: Dict[str, Any]) -> Dict[str, Any]:
    """Typed Strategy definition from a project's native config dict (keys the projects already use; a project
    that does not state one leaves it None). Deployment settings ('live': account, host, port, client id, ...)
    are never part of it."""
    stm = native.get("stm") or {}
    model = stm.get("model") or {}

    def first(*values):
        return next((v for v in values if v is not None), None)

    bar_size = native.get("bar_size_setting")
    return {
        "bar_size": bar_size,
        "bar_frequency": bar_frequency(bar_size, stm.get("bar_minutes")),
        "model_type": first(native.get("model_type"), model.get("model_type")),
        "training_window": first(native.get("training_window"), (stm.get("training") or {}).get("rolling_window_rows")),
        "retrain_every_days": native.get("retrain_every_days"),
        "prediction_horizon": first(native.get("prediction_horizon"), stm.get("prediction_horizon")),
    }
