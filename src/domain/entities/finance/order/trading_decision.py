"""
TradingDecision (P.06.05): what a strategy decided at a bar — the targets it asked for and the model that produced
them. Every order the decision sends carries its id (BrokerOrder.decision_id), so the audit trail reads
decision -> orders -> executions. Append-only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class TradingDecision:
    strategy: str
    bar: datetime                                  # the bar the decision is based on (naive exchange time)
    decided_at: datetime                           # wall clock, UTC naive
    targets: Dict[str, float] = field(default_factory=dict)       # ticker -> target weight
    account: Optional[str] = None
    artifact_id: Optional[int] = None              # model artifact that scored the bar
    note: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.strategy:
            raise ValueError("a trading decision needs its strategy")
