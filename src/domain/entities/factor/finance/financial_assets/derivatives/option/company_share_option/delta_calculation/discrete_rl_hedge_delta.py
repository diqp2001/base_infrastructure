"""DiscreteRLHedgeDelta — Du et al. (2020) discrete-action RL hedger.

Reference
---------
Du, J., Jin, M., Kolm, P.N., Tichavsky, P. & Yordanov, Y. (2020).
"Deep Reinforcement Learning for Option Replication and Hedging."
Journal of Financial Data Science, 2(4), 44–57.

Design
------
The agent observes a 4-D state vector at each rebalancing step:

    obs = [S_t / K,  τ,  n_t,  σ_t]

where S_t/K is log-moneyness proxy, τ is time to expiry, n_t is the current
hedge position, and σ_t is the ATM implied volatility.

The policy maps obs → a discrete action index.  The action represents a delta
*adjustment* chosen from a finite action space (default: 7 levels ranging from
-10 to +10 delta units).  The new hedge position is:

    δ_new = n_t + action_space[action_idx]

Policy injection
----------------
Pass a `policy` object with a `.predict(obs: list) -> int` method.
When no policy is supplied the method falls back to the standard BS delta so
backtests without a trained model still produce valid (analytical) output.

`is_discrete=True` is always set on DeltaResult so callers know the delta
may need rounding to the nearest tradeable lot.
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

_DEFAULT_ACTION_SPACE: List[float] = [-0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.10]


class DiscreteRLHedgeDelta(DeltaCalculationMethod):
    """Du et al. (2020) discrete-action RL hedger.

    Parameters
    ----------
    policy:
        Object with `.predict(obs: list) -> int`.  None → BS fallback.
    action_space:
        Ordered list of delta adjustments the policy can choose.  The policy
        returns an index into this list.
    """

    def __init__(
        self,
        policy=None,
        action_space: Optional[List[float]] = None,
    ) -> None:
        self._policy = policy
        self._action_space: List[float] = (
            list(action_space) if action_space is not None else list(_DEFAULT_ACTION_SPACE)
        )

    @property
    def method_name(self) -> str:
        return "discrete_rl_hedge"

    def compute_delta(self, state: OptionMarketState) -> DeltaResult:
        if self._policy is None:
            return DeltaResult(
                delta=self._bs_delta(state),
                method_name=self.method_name,
                diagnostics={"fallback": "bs", "reason": "no_policy"},
                is_discrete=True,
            )

        obs = self._encode_state(state)
        action_idx = int(self._policy.predict(obs))

        # Clamp out-of-range index to neutral (middle of action space)
        if not 0 <= action_idx < len(self._action_space):
            action_idx = len(self._action_space) // 2

        delta_adjustment = self._action_space[action_idx]
        new_delta = state.current_hedge_position + delta_adjustment

        return DeltaResult(
            delta=new_delta,
            method_name=self.method_name,
            diagnostics={
                "action_idx": action_idx,
                "delta_adjustment": delta_adjustment,
                "obs": obs,
            },
            is_discrete=True,
        )

    def _encode_state(self, state: OptionMarketState) -> List[float]:
        """4-D state: [S/K, τ, n_t, σ]."""
        moneyness = state.spot / state.strike if state.strike > 0 else 1.0
        return [moneyness, state.tau, state.current_hedge_position, state.implied_vol]
