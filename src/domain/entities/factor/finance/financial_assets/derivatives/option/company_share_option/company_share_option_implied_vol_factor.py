import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import CompanyShareOptionValueFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionImpliedVolFactor(CompanyShareOptionFactor):
    """Implied volatility of a single company share option via Newton-Raphson inversion.

    Resolution branch: A.  Dependencies:
    - CompanyShareOptionFactor (IBKR option market price)
    - CompanyShareValueFactor  (underlying stock price S)
    - CompanyShareOptionRFYieldFactor (risk-free rate r; required — returns None if unavailable)

    Strike K and time-to-expiry T are read directly from the option entity passed via
    the entity= kwarg injected by the resolution service.
    """

    def __init__(
        self,
        name: str = "implied_vol",
        group: str = "volatility",
        subgroup: Optional[str] = "implied",
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
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import CompanyShareOptionRFYieldFactor
        return [
            DependencySpec(
                factor_type=CompanyShareOptionValueFactor,
                group="value",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareValueFactor,
                group="value",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
            DependencySpec(
                factor_type=CompanyShareOptionRFYieldFactor,
                group="fundamental",
                frequency=DependencySpec.SELF,
                source_in=["calculated"],
            ),
        ]
    

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Compute implied vol from option market price (IBKR) via Newton-Raphson B-S inversion."""
        entity = dependencies.get("entity")
        target_date = dependencies.get("target_date")
        raw = dependencies.get("CompanyShareOptionValueFactor")
        if raw is None:
            return None
        values = raw if isinstance(raw, list) else [raw]
        prices = [float(v) for v in values if v is not None and float(v) > 0]
        if not prices:
            return None
        market_price = sum(prices) / len(prices)
        if market_price <= 0:
            return None

        # stock price S from CompanyShareValueFactor dependency
        raw_s = dependencies.get("CompanyShareValueFactor")
        if raw_s is None:
            return None
        s_values = raw_s if isinstance(raw_s, list) else [raw_s]
        s_values = [float(v) for v in s_values if v is not None and float(v) > 0]
        if not s_values:
            return None
        stock_price = sum(s_values) / len(s_values)

        # strike K and time-to-expiry T from option entity attributes
        if entity is None:
            return None
        strike_price = getattr(entity, 'strike_price', None)
        if strike_price is None:
            return None
        strike_price = float(strike_price)

        expiry_date = getattr(entity, 'end_date', None)
        if expiry_date is None:
            expiry_str = getattr(entity, 'expiry', None)
            if expiry_str:
                from datetime import datetime as _dt
                expiry_date = _dt.strptime(str(expiry_str), '%Y%m%d').date()
        if expiry_date is None:
            return None

        if target_date is not None:
            ref_date = target_date.date() if hasattr(target_date, 'date') else target_date
        else:
            from datetime import date as _date
            ref_date = _date.today()

        if hasattr(expiry_date, 'date'):
            expiry_date = expiry_date.date()

        days_to_expiry = (expiry_date - ref_date).days
        if days_to_expiry <= 0:
            return None
        time_to_expiry = days_to_expiry / 365.0

        # risk-free rate r — must come from CompanyShareOptionRFYieldFactor dependency
        raw_r = dependencies.get("CompanyShareOptionRFYieldFactor")
        if raw_r is None:
            return None
        r_values = raw_r if isinstance(raw_r, list) else [raw_r]
        r_values = [float(v) for v in r_values if v is not None]
        if not r_values:
            return None
        risk_free_rate = sum(r_values) / len(r_values)

        option_type = getattr(entity, 'option_type', 'call') or 'call'

        return self.compute_iv(
            market_price=market_price,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiry=time_to_expiry,
            option_type=option_type,
        )

    def compute_iv(
        self,
        market_price: float,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> Optional[float]:
        """Newton-Raphson inversion of Black-Scholes; bisection fallback for deep OTM."""
        if market_price <= 0 or stock_price <= 0 or strike_price <= 0 or time_to_expiry <= 0:
            return None

        # Improved initial guess: Brenner-Subrahmanyam approximation
        vol = math.sqrt(2 * math.pi / time_to_expiry) * market_price / stock_price
        vol = max(0.01, min(vol, 10.0))

        for _ in range(max_iterations):
            price, vega = self._bs_price_and_vega(
                stock_price, strike_price, risk_free_rate, vol, time_to_expiry,
                option_type, dividend_yield,
            )
            if price is None or vega is None or abs(vega) < 1e-10:
                break
            diff = price - market_price
            if abs(diff) < tolerance:
                return vol
            step = diff / vega
            vol -= step
            # Clamp to avoid divergence on deep OTM options
            vol = max(0.0001, min(vol, 20.0))

        # N-R did not converge — fall back to bisection on [0.0001, 20.0]
        lo, hi = 0.0001, 20.0
        price_lo, _ = self._bs_price_and_vega(
            stock_price, strike_price, risk_free_rate, lo, time_to_expiry, option_type, dividend_yield)
        price_hi, _ = self._bs_price_and_vega(
            stock_price, strike_price, risk_free_rate, hi, time_to_expiry, option_type, dividend_yield)
        if price_lo is None or price_hi is None:
            return None
        # Market price must be bracketed
        if not (price_lo <= market_price <= price_hi or price_hi <= market_price <= price_lo):
            return None
        for _ in range(100):
            mid = (lo + hi) / 2.0
            price_mid, _ = self._bs_price_and_vega(
                stock_price, strike_price, risk_free_rate, mid, time_to_expiry, option_type, dividend_yield)
            if price_mid is None:
                return None
            if abs(price_mid - market_price) < tolerance:
                return mid
            if (price_mid - market_price) * (price_lo - market_price) < 0:
                hi = mid
                price_hi = price_mid
            else:
                lo = mid
                price_lo = price_mid
        return (lo + hi) / 2.0

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _bs_price_and_vega(self, S, K, r, sigma, T, option_type, q):
        try:
            sqrt_T = math.sqrt(T)
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
            d2 = d1 - sigma * sqrt_T
            Se_qT = S * math.exp(-q * T)
            Ke_rT = K * math.exp(-r * T)
            n_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
            vega = Se_qT * n_d1 * sqrt_T
            if option_type.lower() == "call":
                price = Se_qT * self._norm_cdf(d1) - Ke_rT * self._norm_cdf(d2)
            else:
                price = Ke_rT * self._norm_cdf(-d2) - Se_qT * self._norm_cdf(-d1)
            return price, vega
        except (ValueError, ZeroDivisionError):
            return None, None
