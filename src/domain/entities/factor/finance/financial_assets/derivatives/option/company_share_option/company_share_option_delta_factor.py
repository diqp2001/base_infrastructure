import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import (
    CompanyShareOptionFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
    CompanyShareValueFactor,
)


class CompanyShareOptionDeltaFactor(CompanyShareOptionFactor):
    """BSM delta (∂V/∂S) of a single company share option.

    Resolution branch: A.  Dependencies:
    - CompanyShareValueFactor            (underlying stock price S)
    - CompanyShareOptionImpliedVolFactor (implied volatility σ)
    - CompanyShareOptionRFYieldFactor    (risk-free rate r)

    Strike K, time-to-expiry T, and option_type are read directly from the
    option entity passed via the entity= kwarg injected by the resolution service.
    """

    def __init__(
        self,
        name: str = "delta",
        group: str = "greek",
        subgroup: Optional[str] = "delta",
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
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
            CompanyShareOptionImpliedVolFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import (
            CompanyShareOptionRFYieldFactor,
        )

        return [
            DependencySpec(
                factor_type=CompanyShareValueFactor,
                group="value",
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareOptionImpliedVolFactor,
                group="volatility",
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareOptionRFYieldFactor,
                group="fundamental",
            ),
        ]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Compute BSM delta from resolved factor dependencies + option contract attributes."""
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")

        # --- underlying price S ---
        raw_s = dependencies.get("CompanyShareValueFactor")
        if raw_s is None:
            return None
        s_values = raw_s if isinstance(raw_s, list) else [raw_s]
        s_values = [float(v) for v in s_values if v is not None and float(v) > 0]
        if not s_values:
            return None
        stock_price = sum(s_values) / len(s_values)

        # --- implied volatility σ ---
        raw_sigma = dependencies.get("CompanyShareOptionImpliedVolFactor")
        if raw_sigma is None:
            return None
        sigma_values = raw_sigma if isinstance(raw_sigma, list) else [raw_sigma]
        sigma_values = [float(v) for v in sigma_values if v is not None and float(v) > 0]
        if not sigma_values:
            return None
        sigma = sum(sigma_values) / len(sigma_values)

        # --- risk-free rate r ---
        raw_r = dependencies.get("CompanyShareOptionRFYieldFactor")
        if raw_r is None:
            return None
        r_values = raw_r if isinstance(raw_r, list) else [raw_r]
        r_values = [float(v) for v in r_values if v is not None]
        if not r_values:
            return None
        risk_free_rate = sum(r_values) / len(r_values)

        # --- contract attributes from entity ---
        if entity is None:
            return None
        strike_price = getattr(entity, "strike_price", None)
        if strike_price is None:
            return None
        strike_price = float(strike_price)

        expiry_date = getattr(entity, "end_date", None)
        if expiry_date is None:
            expiry_str = getattr(entity, "expiry", None)
            if expiry_str:
                from datetime import datetime as _dt
                expiry_date = _dt.strptime(str(expiry_str), "%Y%m%d").date()
        if expiry_date is None:
            return None

        if target_date is not None:
            ref_date = target_date.date() if hasattr(target_date, "date") else target_date
        else:
            from datetime import date as _date
            ref_date = _date.today()

        if hasattr(expiry_date, "date"):
            expiry_date = expiry_date.date()

        days_to_expiry = (expiry_date - ref_date).days
        if days_to_expiry <= 0:
            return None
        time_to_expiry = days_to_expiry / 365.0

        option_type = getattr(entity, "option_type", "call") or "call"
        dividend_yield = float(getattr(entity, "dividend_yield", 0.0) or 0.0)

        return self.compute_delta(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            sigma=sigma,
            time_to_expiry=time_to_expiry,
            option_type=option_type,
            dividend_yield=dividend_yield,
        )

    def compute_delta(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        sigma: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
    ) -> Optional[float]:
        """BSM delta: exp(-q·T)·N(d₁) for calls, exp(-q·T)·(N(d₁)-1) for puts."""
        side = self._option_side(option_type)
        if side is None or stock_price <= 0 or strike_price <= 0 or sigma <= 0 or time_to_expiry <= 0:
            return None
        try:
            sqrt_T = math.sqrt(time_to_expiry)
            d1 = (
                math.log(stock_price / strike_price)
                + (risk_free_rate - dividend_yield + 0.5 * sigma ** 2) * time_to_expiry
            ) / (sigma * sqrt_T)
            exp_qT = math.exp(-dividend_yield * time_to_expiry)
            nd1 = self._norm_cdf(d1)
            if side == "call":
                return exp_qT * nd1
            return exp_qT * (nd1 - 1.0)
        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
