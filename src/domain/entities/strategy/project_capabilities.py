"""
What a strategy project implementation can do, declared by the project itself (no folder-name conditionals).

``output_contract`` says what the model produces, so a portfolio rule is only offered for outputs it can interpret
(a class probability is not an expected return). ``unsupported`` lists, in plain words, the options the task asks
for that the project does not implement: the UI shows them as unavailable and validation rejects them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

# what one model output per asset means
PROBABILITY_ABOVE_MEDIAN = "probability_above_median"   # P(next return > cross-sectional median), in [0, 1]
POSITION_SIGNAL = "position_signal"                     # signed position size, in [-1, 1]
EXPECTED_RETURN = "expected_return"                     # forecast of the return itself

OUTPUT_CONTRACTS: Dict[str, str] = {
    PROBABILITY_ABOVE_MEDIAN: "Probability that the asset's next-period return beats the cross-sectional median "
                              "(a ranking score, not an expected return)",
    POSITION_SIGNAL: "Signed position signal in [-1, 1] learned by maximising the Sharpe ratio of the positions",
    EXPECTED_RETURN: "Forecast of the next-period return",
}

# portfolio rules -> the outputs they can interpret
PORTFOLIO_RULES: Dict[str, Tuple[str, ...]] = {
    # long the top / short the bottom quantile of the scores, inverse-volatility weights per side, dollar-neutral
    "quantile_long_short_inverse_vol": (PROBABILITY_ABOVE_MEDIAN, EXPECTED_RETURN, POSITION_SIGNAL),
    # w = signal x target_vol / (annualised vol x N), gross capped
    "vol_scaled_signal": (POSITION_SIGNAL,),
}


@dataclass(frozen=True)
class ProjectCapabilities:
    key: str
    label: str
    strategy_type: str                         # e.g. 'cross_sectional_classifier', 'spatio_temporal_momentum'
    description: str
    folder: str                                # the project folder the adapter wraps (informative)
    model_families: Tuple[str, ...]            # model families implemented AND tested
    output_contract: str
    portfolio_rules: Tuple[str, ...]
    long_short: bool
    long_only: bool
    decision_frequencies: Tuple[str, ...]      # e.g. ('1 day',)
    universe_modes: Tuple[str, ...]            # e.g. ('explicit', 'sector_sample')
    lifecycle: Tuple[str, ...]                 # e.g. ('backtest',)
    trains_inside_backtest: bool               # retraining happens as the backtest clock advances
    unsupported: Tuple[str, ...] = field(default_factory=tuple)

    def supports_rule(self, rule: str) -> bool:
        return rule in self.portfolio_rules and self.output_contract in PORTFOLIO_RULES.get(rule, ())

    def to_dict(self) -> Dict:
        return {
            "key": self.key, "label": self.label, "strategy_type": self.strategy_type,
            "description": self.description, "folder": self.folder,
            "model_families": list(self.model_families), "output_contract": self.output_contract,
            "output_contract_description": OUTPUT_CONTRACTS.get(self.output_contract, ""),
            "portfolio_rules": list(self.portfolio_rules), "long_short": self.long_short,
            "long_only": self.long_only, "decision_frequencies": list(self.decision_frequencies),
            "universe_modes": list(self.universe_modes), "lifecycle": list(self.lifecycle),
            "trains_inside_backtest": self.trains_inside_backtest, "unsupported": list(self.unsupported),
        }
