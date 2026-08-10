import math
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionImpliedVolFactor(CompanyShareOptionFactor):
    """Implied volatility of a single company share option via Newton-Raphson inversion.

    Resolution branch: A — depends on CompanyShareOptionFactor for the option market price
    fetched directly from IBKR.  The resolution service delivers the IBKR price through
    dependencies["CompanyShareOptionFactor"].

    Full Newton-Raphson computation also requires stock price (S), strike (K), risk-free
    rate (r), and time to expiry (T) from the option contract entity.  Those parameters are
    not yet threaded through the factor resolution chain; until they are, calculate() returns
    None and the value is not persisted.
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
        return ["CompanyShareOptionFactor"]

    def calculate(self, dependencies: dict) -> Optional[float]:
        """Compute implied vol from option market price (IBKR) via Newton-Raphson B-S inversion.

        Requires stock price, strike, risk-free rate, and time to expiry from the option
        contract entity — not yet available via the resolution chain; returns None until
        those parameters are integrated.
        """
        raw = dependencies.get("CompanyShareOptionFactor")
        if raw is None:
            return None
        values = raw if isinstance(raw, list) else [raw]
        prices = [float(v) for v in values if v is not None and float(v) > 0]
        if not prices:
            return None
        market_price = sum(prices) / len(prices)
        if market_price <= 0:
            return None
        # S, K, r, T come from the option contract entity — not yet integrated
        return None

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
        """Newton-Raphson inversion of Black-Scholes to find implied volatility."""
        if market_price <= 0 or stock_price <= 0 or strike_price <= 0 or time_to_expiry <= 0:
            return None

        vol = 0.2
        for _ in range(max_iterations):
            price, vega = self._bs_price_and_vega(
                stock_price, strike_price, risk_free_rate, vol, time_to_expiry,
                option_type, dividend_yield,
            )
            if price is None or vega is None or abs(vega) < 1e-10:
                return None
            diff = price - market_price
            if abs(diff) < tolerance:
                return vol
            vol -= diff / vega
            if vol <= 0:
                return None
        return vol

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
