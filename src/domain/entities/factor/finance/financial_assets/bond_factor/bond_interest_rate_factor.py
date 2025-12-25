import math
from typing import Optional
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondInterestRateFactor(BondFactor):
    """Interest rate factor associated with a bond."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Interest Rate",
            group="Bond Factor",
            subgroup="Interest Rate",
            data_type="float",
            source="model",
            definition="Interest rate applied to discount cash flows of the bond.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_interest_rate(self, nominal_rate: float) -> Optional[float]:
        """Simply returns the interest rate."""
        if nominal_rate is None:
            return None
        return nominal_rate
    
    import math
from typing import Optional
import numpy as np

class BondInterestRateFactor(BondFactor):
    """Interest rate factor associated with a bond."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Interest Rate",
            group="Bond Factor",
            subgroup="Interest Rate",
            data_type="float",
            source="model",
            definition="Interest rate applied to discount cash flows of the bond.",
            factor_id=factor_id,
            **kwargs,
        )

    def calculate_interest_rate(self, nominal_rate: float) -> Optional[float]:
        """Simply returns the interest rate."""
        if nominal_rate is None:
            return None
        return nominal_rate

    # -------------------------
    # 1. Hull-White one-factor model
    # -------------------------
    def hull_white_rate(
        self,
        r0: float,
        theta: float,
        kappa: float,
        sigma: float,
        dt: float = 1/252
    ) -> float:
        """
        Simulate next short rate using Hull-White model:
        dr = kappa*(theta - r)*dt + sigma*dW
        
        Args:
            r0: Current short rate
            theta: Long-term mean rate
            kappa: Mean reversion speed
            sigma: Volatility
            dt: Time step (default 1/252 ~ daily)
        Returns:
            Simulated next short rate
        """
        dW = np.random.normal(0, math.sqrt(dt))
        r_next = r0 + kappa * (theta - r0) * dt + sigma * dW
        return max(r_next, 0.0)  # short rate cannot be negative

    # -------------------------
    # 2. Vasicek model
    # -------------------------
    def vasicek_rate(
        self,
        r0: float,
        theta: float,
        kappa: float,
        sigma: float,
        dt: float = 1/252
    ) -> float:
        """
        Vasicek one-factor short rate model:
        dr = kappa*(theta - r)*dt + sigma*dW
        """
        dW = np.random.normal(0, math.sqrt(dt))
        r_next = r0 + kappa * (theta - r0) * dt + sigma * dW
        return r_next  # Vasicek allows negative rates

    # -------------------------
    # 3. Two-factor short rate model (G2++ style)
    # -------------------------
    def two_factor_short_rate(
        self,
        x0: float,
        y0: float,
        sigma_x: float,
        sigma_y: float,
        kappa_x: float,
        kappa_y: float,
        rho: float,
        dt: float = 1/252
    ) -> float:
        """
        Two-factor short rate model:
        r = x + y
        dx = -kappa_x * x dt + sigma_x dW1
        dy = -kappa_y * y dt + sigma_y dW2
        Corr(dW1, dW2) = rho
        """
        dW1 = np.random.normal(0, math.sqrt(dt))
        dW2 = rho * dW1 + math.sqrt(1 - rho**2) * np.random.normal(0, math.sqrt(dt))

        x_next = x0 - kappa_x * x0 * dt + sigma_x * dW1
        y_next = y0 - kappa_y * y0 * dt + sigma_y * dW2

        r_next = x_next + y_next
        return r_next

