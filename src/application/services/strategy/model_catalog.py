"""
Which models a strategy can select, and how a model choice is written into a project's config.

* STM-based projects (config has an ``stm`` section): the networks of the STM pipeline (``stm_models.MODEL_MAPPING``):
  tft (Temporal Fusion Transformer), lstm, mlp, slp (single layer), conv (temporal convolution). Each network takes
  its own constructor parameters: switching model keeps only the parameters the new network accepts (a TFT's
  n_heads / emb_dim never reach an LSTM); the TFT needs ``encoder_length`` < lookback, the others ignore it.
* Cross-sectional momentum projects (``csm``): LightGBM (the classifier its Optuna search tunes).
* Any other project: the model its config already names (no alternative is wired).
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional

STM_MODEL_LABELS = {
    "tft": "Temporal Fusion Transformer (tft)",
    "lstm": "LSTM (lstm)",
    "mlp": "Multi-layer perceptron (mlp)",
    "slp": "Single-layer perceptron (slp)",
    "conv": "Temporal convolution network (conv)",
}
CSM_MODELS = ("lightgbm",)
# constructor arguments that are not model hyper-parameters
_NOT_PARAMS = {"self", "input_dim", "output_dim", "timsteps", "timesteps", "cat_info"}


def _stm_mapping():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_models import MODEL_MAPPING
    return MODEL_MAPPING


def model_choices(config: Dict[str, Any]) -> List[str]:
    """Model types this project's pipeline can train."""
    if isinstance(config.get("stm"), dict):
        return sorted(_stm_mapping(), key=lambda m: (m != "tft", m))
    if isinstance(config.get("csm"), dict):
        return list(CSM_MODELS)
    current = config.get("model_type")
    return [str(current)] if current else []


def model_label(model_type: str) -> str:
    return STM_MODEL_LABELS.get(model_type, model_type)


def stm_model_parameters(model_type: str) -> Dict[str, Any]:
    """{parameter: default} the STM network ``model_type`` accepts."""
    cls = _stm_mapping()[model_type]
    return {name: p.default for name, p in inspect.signature(cls.__init__).parameters.items()
            if name not in _NOT_PARAMS and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}


def apply_model(config: Dict[str, Any], model_type: Optional[str]) -> Dict[str, Any]:
    """Write ``model_type`` into the config (in place): top-level key, and for STM the network with only the
    parameters it accepts. Raises ValueError for a model the project cannot train."""
    if not model_type:
        return config
    choices = model_choices(config)
    if choices and model_type not in choices:
        raise ValueError(f"model '{model_type}' is not available for this project (choices: {', '.join(choices)})")
    config["model_type"] = model_type
    stm = config.get("stm")
    if isinstance(stm, dict):
        model = dict(stm.get("model") or {})
        accepted = stm_model_parameters(model_type)
        model["model_type"] = model_type
        model["params"] = {k: v for k, v in (model.get("params") or {}).items() if k in accepted}
        # new dicts, never the project's own: get_config() copies are shallow
        # (the network wrapper runs a TFT on the CPU unless told otherwise)
        config["stm"] = {**stm, "model": model}
    return config
