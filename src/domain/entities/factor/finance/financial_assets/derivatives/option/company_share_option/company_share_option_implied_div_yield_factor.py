import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionImpliedDivYieldFactor(CompanyShareOptionFactor):
    """Implied dividend yield of a company share derived from put-call parity."""

    def __init__(
        self,
        name: str = "implied_div_yield",
        group: str = "fundamental",
        subgroup: Optional[str] = "daily",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
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
            frequency=frequency,
            **kwargs,
        )

    @property
    def calculate_dependencies(self) -> list:
        return ["CompanyShareOptionFactor"]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Compute implied dividend yield from put-call parity using option price from IBKR.

        Requires call price, put price, stock price, strike, risk-free rate, and time to
        expiry.  Currently only the option market price is available from CompanyShareOptionFactor;
        the remaining contract details will be integrated from the option entity when available.
        """
        raw = dependencies.get("CompanyShareOptionFactor")
        if raw is None:
            return None
        values = raw if isinstance(raw, list) else [raw]
        prices = [float(v) for v in values if v is not None and float(v) > 0]
        if not prices:
            return None
        # Full put-call parity inversion requires call, put, S, K, r, T — not yet integrated
        return None

    def compute_implied_div_yield(
        self,
        call_price: float,
        put_price: float,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiry: float,
    ) -> Optional[float]:
        """Infer dividend yield from put-call parity: C - P = S*e^(-q*T) - K*e^(-r*T)."""
        if stock_price <= 0 or strike_price <= 0 or time_to_expiry <= 0:
            return None
        forward_equiv = call_price - put_price + strike_price * math.exp(-risk_free_rate * time_to_expiry)
        if forward_equiv <= 0:
            return None
        return -math.log(forward_equiv / stock_price) / time_to_expiry
