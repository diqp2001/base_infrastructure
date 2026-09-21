from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DeltaResult:
    """Output of a single DeltaCalculationMethod.compute_delta() call.

    `delta`        – target hedge ratio (signed, in underlying units per option).
    `method_name`  – identifier of the method that produced this result.
    `diagnostics`  – method-specific intermediate values for logging/debugging.
    `is_discrete`  – True when the method operates on a discrete action space
                     (e.g. Du et al. 2020); the caller should round delta to the
                     nearest tradeable lot before executing.
    `should_hedge` – None means "always hedge"; True/False gives the method's
                     rebalancing recommendation (used by vol-trigger methods).
    """

    delta: float
    method_name: str
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    is_discrete: bool = False
    should_hedge: Optional[bool] = None
