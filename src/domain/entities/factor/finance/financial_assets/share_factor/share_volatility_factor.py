"""
src/domain/entities/factor/share_volatility_factor.py

ShareVolatilityFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
import random
from typing import Optional, List
import math
from .share_factor import ShareFactor


class ShareVolatilityFactor(ShareFactor):
    """Domain entity representing a share volatility factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        volatility_type: Optional[str] = None,
        period: Optional[int] = None,
        annualization_factor: Optional[float] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            
        )
        self.volatility_type = volatility_type or "historical"  # e.g., "historical", "realized", "implied"
        self.period = period or 20  # Default 20-day volatility
        self.annualization_factor = annualization_factor or math.sqrt(252)  # Annualize assuming 252 trading days

    def calculate_historical_volatility(self, prices: List[float]) -> Optional[float]:
        """Calculate historical volatility from price series."""
        if not prices or len(prices) < 2:
            return None
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append(math.log(prices[i] / prices[i-1]))
        
        if len(returns) < self.period:
            return None
        
        # Use most recent returns for calculation
        recent_returns = returns[-self.period:]
        
        # Calculate standard deviation
        mean_return = sum(recent_returns) / len(recent_returns)
        variance = sum((r - mean_return) ** 2 for r in recent_returns) / (len(recent_returns) - 1)
        
        if variance < 0:
            return None
        
        daily_volatility = math.sqrt(variance)
        
        # Annualize if requested
        return daily_volatility * self.annualization_factor

    def calculate_realized_volatility(self, intraday_returns: List[float]) -> Optional[float]:
        """Calculate realized volatility from high-frequency intraday returns."""
        if not intraday_returns:
            return None
        
        # Sum of squared returns
        sum_squared_returns = sum(r ** 2 for r in intraday_returns)
        
        # Realized volatility is the square root of sum of squared returns
        return math.sqrt(sum_squared_returns)

    def calculate_volatility_percentile(self, current_volatility: float, historical_volatilities: List[float]) -> Optional[float]:
        """Calculate the percentile rank of current volatility vs historical values."""
        if not historical_volatilities or current_volatility is None:
            return None
        
        sorted_vols = sorted(historical_volatilities)
        rank = 0
        
        for vol in sorted_vols:
            if current_volatility > vol:
                rank += 1
            else:
                break
        
        percentile = rank / len(sorted_vols) * 100
        return percentile

    def is_high_volatility(self, threshold: float = 0.3) -> bool:
        """Check if this represents a high volatility measurement."""
        # This would need actual volatility value to determine
        return self.volatility_type in ["high", "extreme"]

    def is_annualized(self) -> bool:
        """Check if this volatility factor is annualized."""
        return self.annualization_factor is not None and self.annualization_factor != 1.0

    def is_intraday_volatility(self) -> bool:
        """Check if this measures intraday volatility."""
        return self.volatility_type.lower() in ["realized", "intraday", "high_frequency"]
    
    # -------------------------
    # 1. Local volatility via SDE
    # -------------------------
    def calculate_local_vol_sde(
        self,
        S: float,
        r: float,
        sigma: float,
        T: float,
        n_paths: int = 10000
    ) -> Optional[float]:
        """Estimate local volatility via Monte Carlo SDE simulation."""
        if S <= 0 or sigma <= 0 or T <= 0:
            return None
        STs = []
        for _ in range(n_paths):
            z = random.gauss(0, 1)
            ST = S * math.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
            STs.append(ST)
        mean = sum(STs) / n_paths
        variance = sum((x - mean)**2 for x in STs) / (n_paths - 1)
        return math.sqrt(variance) / S  # simple local volatility approximation

    # -------------------------
    # 2. Local volatility via PDE
    # -------------------------
    def calculate_local_vol_pde(
        self,
        S: float,
        sigma: float,
        T: float,
        r: float = 0.01,
        M: int = 100,
        N: int = 100
    ) -> Optional[float]:
        """
        Estimate local volatility using a finite-difference approximation of the Black-Scholes PDE.
        
        Args:
            S: Current underlying price
            sigma: Initial volatility estimate
            T: Time to maturity (in years)
            r: Risk-free rate
            M: Number of time steps
            N: Number of price steps
        
        Returns:
            Approximated local volatility at S, T
        """
        if S <= 0 or sigma <= 0 or T <= 0:
            return None

        # Placeholder: simple PDE approximation via gamma (∂²V/∂S²)
        # In a real implementation, a finite difference grid would be created to solve the PDE
        gamma = 0.01  # Placeholder value for gamma
        local_vol = sigma * math.sqrt(abs(gamma))  # crude approximation
        return local_vol


    # -------------------------
    # 3. Dupire local volatility
    # -------------------------
    def calculate_local_vol_dupire(
        self,
        S: float,
        K: float,
        T: float,
        call_prices: List[float],
        strikes: List[float],
        maturities: List[float],
        r: float = 0.01
    ) -> Optional[float]:
        """
        Approximate local volatility using the Dupire formula:
        σ²_loc(K,T) = (∂C/∂T + r K ∂C/∂K) / (0.5 K² ∂²C/∂K²)
        
        Args:
            S: Current underlying price
            K: Strike price
            T: Time to maturity
            call_prices: List of observed call option prices
            strikes: Corresponding strikes
            maturities: Corresponding maturities
            r: Risk-free rate
        
        Returns:
            Local volatility at strike K and maturity T
        """
        if not call_prices or not strikes or not maturities or T <= 0 or K <= 0:
            return None

        # Simple finite difference approximations for derivatives
        # ∂C/∂T
        if len(maturities) > 1:
            dC_dT = (call_prices[-1] - call_prices[0]) / (maturities[-1] - maturities[0])
        else:
            dC_dT = 0.0

        # ∂C/∂K
        if len(strikes) > 1:
            dC_dK = (call_prices[-1] - call_prices[0]) / (strikes[-1] - strikes[0])
            d2C_dK2 = 0.0  # Placeholder: would require multiple strikes to compute second derivative
        else:
            dC_dK = 0.0
            d2C_dK2 = 0.01  # small positive value to avoid division by zero

        numerator = dC_dT + r * K * dC_dK
        denominator = 0.5 * K**2 * max(d2C_dK2, 1e-8)  # avoid division by zero
        local_vol_squared = max(numerator / denominator, 0.0)
        return math.sqrt(local_vol_squared)

        # -------------------------
        # 4. Wilmott approximation
        # -------------------------
    def calculate_local_vol_wilmott(
            self,
            sigma: float,
            T: float
        ) -> Optional[float]:
            """Approximation from Wilmott for local volatility."""
            return sigma * (1 + 0.5 * T)  # simple placeholder

        # -------------------------
        # 5. Heston stochastic volatility model
        # -------------------------
    def calculate_local_vol_heston(
            self,
            S: float,
            v0: float,
            kappa: float,
            theta: float,
            xi: float,
            rho: float,
            r: float,
            T: float,
            n_paths: int = 10000,
            n_steps: int = 100
        ) -> Optional[float]:
            """Heston model local volatility via Monte Carlo simulation."""
            dt = T / n_steps
            STs = []
            for _ in range(n_paths):
                S_t, v_t = S, v0
                for _ in range(n_steps):
                    z1 = random.gauss(0, 1)
                    z2 = rho * z1 + math.sqrt(1 - rho**2) * random.gauss(0, 1)
                    v_t = max(v_t + kappa * (theta - v_t) * dt + xi * math.sqrt(v_t * dt) * z2, 0)
                    S_t = S_t * math.exp((r - 0.5 * v_t) * dt + math.sqrt(v_t * dt) * z1)
                STs.append(S_t)
            mean = sum(STs) / n_paths
            variance = sum((x - mean)**2 for x in STs) / (n_paths - 1)
            return math.sqrt(variance) / S

        # -------------------------
        # 6. SABR model local volatility
        # -------------------------
    def calculate_local_vol_sabr(
            self,
            F: float,
            K: float,
            T: float,
            alpha: float,
            beta: float,
            rho: float,
            nu: float
        ) -> Optional[float]:
            """
            SABR local volatility approximation (Hagan's formula)
            F: forward price, K: strike
            """
            if F <= 0 or K <= 0 or alpha <= 0 or T <= 0:
                return None
            if F == K:
                return alpha * F**(beta - 1)
            logFK = math.log(F / K)
            z = (nu / alpha) * (F * K)**((1 - beta) / 2) * logFK
            x_z = math.log((math.sqrt(1 - 2 * rho * z + z**2) + z - rho) / (1 - rho))
            return alpha * (F * K)**((beta - 1) / 2) * z / x_z