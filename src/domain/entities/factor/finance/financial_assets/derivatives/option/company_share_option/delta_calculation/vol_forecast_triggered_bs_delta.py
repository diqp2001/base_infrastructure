"""VolForecastTriggeredBSDelta — Li et al. (2024) vol-forecast-triggered BS hedger.

Reference
---------
Li, Y., Vasquez, A. & Zhang, B. (2024). "Volatility-Triggered Option Hedging
with Deep Learning." Journal of Financial Economics, 153, 103–127.

Design
------
At each step the method:
  1. Obtains a volatility forecast σ_forecast from an injected MLP forecaster
     (or falls back to the current ATM implied vol when no forecaster is present).
  2. Computes the BS delta using σ_forecast instead of the observed σ_implied.
  3. Decides whether to actually rebalance (should_hedge) based on one of three
     RebalancingTrigger strategies applied to the rolling forecast history:

     MEDIAN       – hedge if σ_forecast > rolling median of prior forecasts.
     PERCENTILE_90 – hedge if σ_forecast > 90th-percentile threshold of priors.
     TREND        – hedge if σ_forecast > previous forecast (upward trend).

The `should_hedge` flag in DeltaResult is True/False (never None) once at
least two forecasts have been accumulated.  On the first observation, the
hedge always fires (True) because there is no reference to compare against.

Forecaster protocol
-------------------
Pass a `vol_forecaster` with `.predict(state: OptionMarketState) -> float`.
The forecaster is stateless from this class's perspective; it may maintain
its own internal state (e.g. LSTM hidden state).
"""

from __future__ import annotations

import statistics
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
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.rebalancing_trigger import (
    RebalancingTrigger,
)


class VolForecastTriggeredBSDelta(DeltaCalculationMethod):
    """Li et al. (2024) vol-forecast-triggered BS delta.

    Parameters
    ----------
    vol_forecaster:
        Object with `.predict(state: OptionMarketState) -> float`.
        None → uses state.implied_vol directly.
    trigger_strategy:
        Which rebalancing trigger to apply (default: MEDIAN).
    trigger_percentile:
        Fraction in (0, 1) used by PERCENTILE_90 (default: 0.90).
    """

    def __init__(
        self,
        vol_forecaster=None,
        trigger_strategy: RebalancingTrigger = RebalancingTrigger.MEDIAN,
        trigger_percentile: float = 0.90,
    ) -> None:
        self._vol_forecaster = vol_forecaster
        self._trigger_strategy = trigger_strategy
        self._trigger_percentile = float(trigger_percentile)
        self._vol_history: List[float] = []

    @property
    def method_name(self) -> str:
        return "vol_forecast_triggered_bs"

    def compute_delta(self, state: OptionMarketState) -> DeltaResult:
        if self._vol_forecaster is not None:
            sigma_forecast = float(self._vol_forecaster.predict(state))
        else:
            sigma_forecast = state.implied_vol

        # BS delta computed with the forecast vol, not the observed implied vol
        forecast_state = OptionMarketState(
            spot=state.spot,
            strike=state.strike,
            tau=state.tau,
            r=state.r,
            q=state.q,
            implied_vol=sigma_forecast,
            realized_vol=state.realized_vol,
            current_hedge_position=state.current_hedge_position,
            option_type=state.option_type,
        )
        delta = self._bs_delta(forecast_state)

        self._vol_history.append(sigma_forecast)
        should_hedge = self._evaluate_trigger(sigma_forecast)

        return DeltaResult(
            delta=delta,
            method_name=self.method_name,
            diagnostics={
                "sigma_forecast": sigma_forecast,
                "sigma_implied": state.implied_vol,
                "trigger_strategy": self._trigger_strategy.value,
                "history_len": len(self._vol_history),
            },
            should_hedge=should_hedge,
        )

    def reset_history(self) -> None:
        """Clear the rolling forecast history (e.g. between backtesting episodes)."""
        self._vol_history.clear()

    # ------------------------------------------------------------------ #
    # Internal trigger logic                                               #
    # ------------------------------------------------------------------ #

    def _evaluate_trigger(self, sigma_forecast: float) -> bool:
        prior = self._vol_history[:-1]  # exclude the just-appended current value
        if len(prior) < 1:
            return True  # always hedge on the first observation

        if self._trigger_strategy == RebalancingTrigger.TREND:
            return sigma_forecast > prior[-1]

        if self._trigger_strategy == RebalancingTrigger.MEDIAN:
            threshold = statistics.median(prior)
        elif self._trigger_strategy == RebalancingTrigger.PERCENTILE_90:
            sorted_prior = sorted(prior)
            idx = min(
                int(len(sorted_prior) * self._trigger_percentile),
                len(sorted_prior) - 1,
            )
            threshold = sorted_prior[idx]
        else:
            return True

        return sigma_forecast > threshold
