"""
A Strategy back into its project's config: what the project runs when a designed strategy is launched.

``apply_strategy(base_config, strategy)`` starts from the project's own DEFAULT_CONFIG (the run / deployment keys,
the factor classes and the objects JSON cannot hold stay as the project defines them) and writes the strategy on it:

* sections   the inverse of ``project_strategy_registration.strategy_sections``: every stored key goes back to its
             place (``stm.<x>`` into the stm section; Portfolio keys merged, its class objects kept); JSON lists become
             the tuples / class-keyed dicts the base config uses;
* universe   ``universe.instruments`` {asset type: symbols} -> ``config['universe']`` {domain class: symbols}; for STM
             projects the explicit ticker list and, when it differs from the project's, a universe name of its own;
* typed      bar_size -> bar_size_setting; bar_frequency ('10m', '1h', '1d': the data bars) -> stm.bar_minutes where
             the project has it (the decision interval is trading.config_interval); model_type (model_catalog.apply_model: only the
             chosen network's parameters); training_window (+ stm rolling_window_rows); retrain_every_days;
             prediction_horizon.

Applying the strategy registered from a config gives that config back (tests check it for every project).
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, Optional

from src.application.services.strategy.model_catalog import apply_model

_PORTFOLIO_KEYS = ("Portfolio", "PORTFOLIO")


def _restore(value: Any, base: Any) -> Any:
    """A JSON value back into the shape of the base config's value (tuples, class keys, classes kept)."""
    from src.application.services.backtest_registry.run_identity import _jsonable
    if base is not None and _jsonable(base) == value:
        return copy.deepcopy(base)                             # unchanged: the project's own object (path, tuple...)
    if isinstance(base, type) or callable(base) and not isinstance(base, (dict, list, tuple)):
        return base                                            # a class / function: JSON only holds its name
    if isinstance(base, tuple) and isinstance(value, list):
        template = base[0] if base else None
        return tuple(_restore(v, base[i] if i < len(base) else template) for i, v in enumerate(value))
    if isinstance(base, list) and isinstance(value, list):
        template = base[0] if base else None
        return [_restore(v, base[i] if i < len(base) else template) for i, v in enumerate(value)]
    if isinstance(base, dict) and isinstance(value, dict):
        by_name = {(k if isinstance(k, str) else getattr(k, "__name__", str(k))): k for k in base}
        out = dict(base)
        for name, v in value.items():
            key = by_name.get(name, name)
            out[key] = _restore(v, base.get(key))
        return out
    return value


def _asset_class(name: str, base_universe: Any):
    """The domain class an asset type name stands for (the base config's own keys first)."""
    if isinstance(base_universe, dict):
        for key in base_universe:
            if getattr(key, "__name__", None) == name:
                return key
    import importlib
    known = {}
    base = "src.domain.entities.finance.financial_assets"
    for type_name, module in (("CompanyShare", "share.company_share.company_share"),
                              ("ETFShare", "share.etf_share.etf_share"),
                              ("CompanyShareOption", "derivatives.option.company_share_option"),
                              ("ETFShareOption", "derivatives.option.etf_share_option"),
                              ("Future", "derivatives.future.future"),
                              ("Index", "index.index"),
                              ("Currency", "currency")):
        try:
            known[type_name] = getattr(importlib.import_module(f"{base}.{module}"), type_name)
        except (ImportError, AttributeError):                  # pragma: no cover
            pass
    if name not in known:
        raise ValueError(f"asset type '{name}' cannot be written into a project config")
    return known[name]


def _minutes(frequency: Optional[str]) -> Optional[int]:
    match = re.fullmatch(r"(\d+)\s*(m|h)", (frequency or "").strip().lower())
    if not match:
        return None
    return int(match.group(1)) * (60 if match.group(2) == "h" else 1)


def apply_strategy(base_config: Dict[str, Any], strategy) -> Dict[str, Any]:
    config = copy.deepcopy(base_config)
    base_request = None
    for section, values in (strategy.sections or {}).items():
        for key, value in (values or {}).items():
            if key == "instruments":
                continue                                        # the universe: below
            if key in ("factors", "FACTORS"):
                continue                                        # factor classes: the project's own definitions
            if key.startswith("stm."):
                stm = config.setdefault("stm", {})
                sub = key[4:]
                stm[sub] = _restore(value, stm.get(sub))
            elif key in _PORTFOLIO_KEYS and isinstance(config.get(key), dict) and isinstance(value, dict):
                config[key] = {**config[key], **{k: _restore(v, config[key].get(k)) for k, v in value.items()
                                                 if not isinstance(config[key].get(k), type)}}
            else:
                config[key] = _restore(value, config.get(key))

    # universe
    from src.application.services.strategy.project_strategy_registration import universe_request
    base_request = universe_request(base_config)
    request = (strategy.sections.get("universe") or {}).get("instruments")
    if request:
        base_universe = base_config.get("universe")
        if "FinancialAsset" in request:
            config["universe"] = list(request["FinancialAsset"])
        else:
            # entries that are not symbol lists (portfolio / option specifications) stay as the project has them
            kept = {k: copy.deepcopy(v) for k, v in base_universe.items()
                    if not isinstance(v, (list, tuple, set))} if isinstance(base_universe, dict) else {}
            config["universe"] = {**kept, **{_asset_class(t, base_universe): list(symbols)
                                             for t, symbols in request.items()}}
        stm_universe = (config.get("stm") or {}).get("universe")
        if isinstance(stm_universe, dict) and request != base_request:
            shares = request.get("CompanyShare")
            if shares:
                stm_universe["tickers"] = list(shares)
            base_name = stm_universe.get("name") or "strategy"
            stm_universe["name"] = f"{base_name}__strategy{strategy.id}"

    # typed definition
    if strategy.bar_size:
        config["bar_size_setting"] = strategy.bar_size
    if strategy.bar_frequency:                                  # the DATA bars; decisions: trading.config_interval
        stm = config.get("stm")
        if isinstance(stm, dict) and "bar_minutes" in stm:
            stm["bar_minutes"] = _minutes(strategy.bar_frequency)   # None = daily bars
    apply_model(config, strategy.model_type)
    if strategy.training_window is not None:
        if "training_window" in base_config:
            config["training_window"] = strategy.training_window
        training = (config.get("stm") or {}).get("training")
        base_training = (base_config.get("stm") or {}).get("training") or {}
        # the rolling window follows only where the project uses one number for both (some STM projects call the
        # model's input window 'training_window')
        if (isinstance(training, dict) and "rolling_window_rows" in training
                and base_config.get("training_window") in (None, base_training.get("rolling_window_rows"))):
            training["rolling_window_rows"] = strategy.training_window
    if strategy.retrain_every_days is not None:
        config["retrain_every_days"] = strategy.retrain_every_days
    if strategy.prediction_horizon is not None:
        if isinstance(config.get("stm"), dict):
            config["stm"]["prediction_horizon"] = strategy.prediction_horizon
        else:
            config["prediction_horizon"] = strategy.prediction_horizon
    return config
