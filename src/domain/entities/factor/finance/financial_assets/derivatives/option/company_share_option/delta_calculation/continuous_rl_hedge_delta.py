"""ContinuousRLHedgeDelta — Bracha et al. (2025) TD3 continuous-action RL hedger.

Reference
---------
Bracha, H., El Bitar, K. & Mrad, M. (2025). "Reinforcement Learning for
Dynamic Delta Hedging." arXiv:2501.XXXXX / submitted to Journal of Derivatives.

Design
------
A TD3 (Twin Delayed Deep Deterministic Policy Gradient) actor maps a 6-D
observation to a *continuous delta adjustment* ΔH ∈ [-action_clip, action_clip]:

    obs = [V_t,  S_t,  τ,  S_t/K,  σ_realised,  n_t]

where:
  V_t          = BSM option price (proxy for current option value)
  S_t          = underlying spot
  τ            = time to expiry
  S_t/K        = moneyness
  σ_realised   = realised volatility (annualised)
  n_t          = current hedge delta

The new hedge position is:
    δ_new = n_t + clip(ΔH, -action_clip, action_clip)

Key difference from the discrete case: the action is an *adjustment* to the
existing hedge, NOT a target delta.  This avoids constant full rebalancing and
is more realistic for a leveraged book.

Policy injection
----------------
Pass a `policy` object with a `.predict(obs: list) -> float` method.
Without a policy the method falls back to the standard BS delta.
"""

from __future__ import annotations

from typing import List, Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_calculation_method import (
    DeltaCalculationMethod,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_result import (
    DeltaResult,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.option_market_state import (
    OptionMarketState,
)


class ContinuousRLHedgeDelta(DeltaCalculationMethod):
    """Bracha et al. (2025) TD3 continuous-action RL hedger.

    Parameters
    ----------
    policy:
        Object with `.predict(obs: list) -> float`.  None → BS fallback.
    action_clip:
        Symmetric bound on the delta adjustment per step (default 1.0).
    """

    def __init__(
        self,
        policy=None,
        action_clip: float = 1.0,
    ) -> None:
        self._policy = policy
        self._action_clip = float(action_clip)

    @property
    def method_name(self) -> str:
        return "continuous_rl_hedge"

    def compute_delta(self, state: OptionMarketState) -> DeltaResult:
        if self._policy is None:
            return DeltaResult(
                delta=self._bs_delta(state),
                method_name=self.method_name,
                diagnostics={"fallback": "bs", "reason": "no_policy"},
            )

        obs = self._encode_state_6d(state)
        raw_action = float(self._policy.predict(obs))
        clipped = max(-self._action_clip, min(self._action_clip, raw_action))
        new_delta = state.current_hedge_position + clipped

        return DeltaResult(
            delta=new_delta,
            method_name=self.method_name,
            diagnostics={
                "raw_action": raw_action,
                "clipped_action": clipped,
                "obs": obs,
            },
        )

    def _encode_state_6d(self, state: OptionMarketState) -> List[float]:
        """6-D state: [V_t, S_t, τ, S_t/K, σ_realised, n_t]."""
        option_price = self._bs_price(state)
        moneyness = state.spot / state.strike if state.strike > 0 else 1.0
        return [
            option_price,
            state.spot,
            state.tau,
            moneyness,
            state.realized_vol,
            state.current_hedge_position,
        ]
