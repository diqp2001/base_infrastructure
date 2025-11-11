from __future__ import annotations

import pandas as pd
from typing import Optional
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import FactorShare


class MomentumFactorShare(FactorShare):
    """Specialized momentum factor for equity instruments."""

    def __init__(
        self,
        name: str,
        group: str = "momentum",
        subgroup: Optional[str] = None,
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "spatiotemporal_engineering",
        definition: Optional[str] = "Momentum-based share factor",
        equity_specific: Optional[str] = "momentum",
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            equity_specific=equity_specific,
            factor_id=factor_id,
        )


