from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


class CompanyShareOptionFactor(OptionFactor):
    """Factor for options whose underlying is a company share."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            **kwargs,
        )

    @staticmethod
    def _option_side(option_type) -> "str | None":
        """'call' / 'put' from 'call' / 'put' / IBKR rights 'C' / 'P' (any case); None otherwise.

        An unrecognised option type is never priced (it used to fall through to the put branch,
        so an IBKR 'C' right was valued as a put)."""
        side = str(option_type or "").strip().lower()
        return {"call": "call", "c": "call", "put": "put", "p": "put"}.get(side)

