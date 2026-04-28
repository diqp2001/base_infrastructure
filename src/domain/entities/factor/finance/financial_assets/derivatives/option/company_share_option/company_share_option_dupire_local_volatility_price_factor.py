import math
import random
from typing import Optional, Callable

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionDupireLocalVolatilityPriceFactor(CompanyShareOptionFactor):
    """Dupire Local Volatility price factor for company share options."""

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

    def calculate(
        self,
        S: float,          # underlying price
        K: float,          # strike price
        r: float,          # risk-free rate
        T: float,          # time to maturity in years
        local_vol_func: Optional[Callable[[float, float], float]] = None,  # σ_LV(S,t)
        q: float = 0.0,    # dividend yield
        option_type: str = "call",
        n_paths: int = 50000,  # number of Monte Carlo paths
        n_steps: int = 252,    # number of time steps per year
        volatility_surface: Optional[dict] = None,  # market volatility surface
    ) -> Optional[float]:
        """
        Calculate option price using Dupire Local Volatility model via Monte Carlo.
        
        The local volatility model assumes:
        dS = (r - q)*S*dt + σ_LV(S,t)*S*dW
        
        Where σ_LV(S,t) is the local volatility function derived from market prices
        using Dupire's formula:
        σ_LV^2(K,T) = [∂C/∂T + (r-q)*K*∂C/∂K + q*C] / [0.5*K^2*∂²C/∂K²]
        """
        if S <= 0 or K <= 0 or T <= 0:
            return None

        try:
            # If no local volatility function provided, use a simple parameterization
            if local_vol_func is None:
                local_vol_func = self._default_local_vol_function

            dt = T / n_steps
            sqrt_dt = math.sqrt(dt)
            
            payoffs = []
            
            for _ in range(n_paths):
                S_t = S
                
                for i in range(n_steps):
                    t = i * dt
                    
                    # Get local volatility at current (S,t)
                    local_vol = local_vol_func(S_t, t)
                    if local_vol <= 0:
                        local_vol = 0.01  # Small positive value to avoid issues
                    
                    # Generate random number
                    z = random.gauss(0, 1)
                    
                    # Update asset price using Euler-Maruyama scheme
                    dS = (r - q) * S_t * dt + local_vol * S_t * sqrt_dt * z
                    S_t += dS
                    S_t = max(S_t, 0)  # Ensure price remains positive
                
                # Calculate payoff
                if option_type.lower() == "call":
                    payoff = max(S_t - K, 0)
                else:  # put
                    payoff = max(K - S_t, 0)
                
                payoffs.append(payoff)
            
            # Discount the expected payoff
            option_price = math.exp(-r * T) * sum(payoffs) / len(payoffs)
            return option_price

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _default_local_vol_function(self, S: float, t: float) -> float:
        """
        Default local volatility function with level-dependent volatility.
        This is a simple parametric form for demonstration.
        """
        # Simple CEV-like local volatility: σ(S,t) = σ₀ * (S/S₀)^(β-1)
        sigma_0 = 0.2  # Base volatility
        S_0 = 100      # Reference spot price
        beta = 0.7     # CEV exponent
        
        return sigma_0 * pow(S / S_0, beta - 1)

    def calibrate_local_volatility_surface(
        self,
        market_prices: dict,  # {(K, T): market_price}
        r: float,
        q: float = 0.0,
        S0: float = 100,
    ) -> Optional[Callable[[float, float], float]]:
        """
        Calibrate local volatility surface from market option prices using Dupire's formula.
        
        This is a simplified implementation. In practice, sophisticated numerical
        methods would be used with regularization techniques.
        """
        try:
            # Convert market prices to implied volatilities first
            implied_vols = {}
            
            for (K, T), price in market_prices.items():
                impl_vol = self._implied_volatility_from_price(price, S0, K, r, T, q)
                if impl_vol is not None and impl_vol > 0:
                    implied_vols[(K, T)] = impl_vol

            if not implied_vols:
                return None

            # Create interpolation of implied volatility surface
            def interpolated_impl_vol(K: float, T: float) -> float:
                # Simple nearest neighbor interpolation (for demonstration)
                min_dist = float('inf')
                best_vol = 0.2  # Default
                
                for (K_market, T_market), vol in implied_vols.items():
                    dist = math.sqrt((K - K_market)**2 + (T - T_market)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_vol = vol
                
                return best_vol

            # Convert to local volatility using finite differences
            def local_vol_function(S: float, t: float) -> float:
                try:
                    # Use current spot as strike for local volatility calculation
                    K = S
                    T_remaining = max(t, 1e-6)  # Avoid division by zero
                    
                    # Get implied volatility and its derivatives (finite differences)
                    dK = S * 0.01  # 1% shift
                    dT = min(T_remaining * 0.01, 0.01)  # Small time shift
                    
                    # Central differences for derivatives
                    sigma_0 = interpolated_impl_vol(K, T_remaining)
                    
                    # ∂σ/∂K
                    sigma_up = interpolated_impl_vol(K + dK, T_remaining)
                    sigma_down = interpolated_impl_vol(K - dK, T_remaining)
                    dsigma_dK = (sigma_up - sigma_down) / (2 * dK)
                    
                    # ∂σ/∂T
                    if T_remaining + dT < 5.0:  # Reasonable time limit
                        sigma_T_up = interpolated_impl_vol(K, T_remaining + dT)
                        dsigma_dT = (sigma_T_up - sigma_0) / dT
                    else:
                        dsigma_dT = 0
                    
                    # Dupire's formula (simplified)
                    d1 = (math.log(S0 / K) + (r - q + 0.5 * sigma_0**2) * T_remaining) / (sigma_0 * math.sqrt(T_remaining))
                    
                    numerator = sigma_0**2 + 2 * sigma_0 * T_remaining * (dsigma_dT + (r - q) * K * dsigma_dK)
                    denominator = (1 + K * d1 * math.sqrt(T_remaining) * dsigma_dK)**2
                    
                    if denominator > 0 and numerator > 0:
                        local_vol_squared = numerator / denominator
                        return math.sqrt(max(local_vol_squared, 1e-6))
                    else:
                        return sigma_0  # Fallback to implied volatility

                except (ValueError, ZeroDivisionError, OverflowError):
                    return 0.2  # Default volatility

            return local_vol_function

        except Exception:
            return None

    def _implied_volatility_from_price(
        self,
        price: float,
        S: float,
        K: float,
        r: float,
        T: float,
        q: float = 0.0,
        option_type: str = "call",
    ) -> Optional[float]:
        """
        Calculate implied volatility from option price using Newton-Raphson method.
        """
        if price <= 0 or S <= 0 or K <= 0 or T <= 0:
            return None

        try:
            # Initial guess
            sigma = 0.2
            
            for _ in range(100):  # Maximum iterations
                # Calculate Black-Scholes price and vega
                d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)
                
                if option_type.lower() == "call":
                    bs_price = S * math.exp(-q * T) * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
                else:  # put
                    bs_price = K * math.exp(-r * T) * self._norm_cdf(-d2) - S * math.exp(-q * T) * self._norm_cdf(-d1)
                
                # Vega
                vega = S * math.exp(-q * T) * self._norm_pdf(d1) * math.sqrt(T)
                
                if abs(vega) < 1e-10:
                    break
                
                # Newton-Raphson update
                diff = bs_price - price
                if abs(diff) < 1e-8:
                    break
                
                sigma_new = sigma - diff / vega
                sigma = max(sigma_new, 1e-6)  # Keep positive
                
                if abs(sigma_new - sigma) < 1e-8:
                    break

            return sigma if sigma > 1e-6 else None

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def calculate_pde_solution(
        self,
        S: float,
        K: float,
        r: float,
        T: float,
        local_vol_func: Callable[[float, float], float],
        q: float = 0.0,
        option_type: str = "call",
        S_max: float = None,
        M: int = 100,      # spatial grid points
        N: int = 100,      # time steps
    ) -> Optional[float]:
        """
        Solve the local volatility PDE using finite difference methods.
        
        PDE: ∂V/∂t + 0.5*σ²(S,t)*S²*∂²V/∂S² + (r-q)*S*∂V/∂S - r*V = 0
        """
        if S <= 0 or K <= 0 or T <= 0:
            return None

        try:
            if S_max is None:
                S_max = 3 * max(S, K)

            dS = S_max / M
            dt = T / N
            
            # Initialize grids
            S_grid = [i * dS for i in range(M + 1)]
            V_grid = [[0.0 for _ in range(M + 1)] for _ in range(N + 1)]
            
            # Terminal condition
            for i in range(M + 1):
                if option_type.lower() == "call":
                    V_grid[N][i] = max(S_grid[i] - K, 0)
                else:  # put
                    V_grid[N][i] = max(K - S_grid[i], 0)
            
            # Backward time stepping
            for j in reversed(range(N)):
                t = j * dt
                
                for i in range(1, M):
                    S_i = S_grid[i]
                    local_vol = local_vol_func(S_i, t)
                    
                    # Finite difference coefficients
                    alpha = 0.5 * dt * (local_vol**2 * S_i**2 / dS**2 - (r - q) * S_i / dS)
                    beta = 1 + dt * (local_vol**2 * S_i**2 / dS**2 + r)
                    gamma = -0.5 * dt * (local_vol**2 * S_i**2 / dS**2 + (r - q) * S_i / dS)
                    
                    # Update using explicit scheme
                    V_grid[j][i] = (alpha * V_grid[j + 1][i - 1] + 
                                   (2 - beta) * V_grid[j + 1][i] + 
                                   gamma * V_grid[j + 1][i + 1])
                
                # Boundary conditions
                if option_type.lower() == "call":
                    V_grid[j][0] = 0
                    V_grid[j][M] = S_max - K * math.exp(-r * (N - j) * dt)
                else:  # put
                    V_grid[j][0] = K * math.exp(-r * (N - j) * dt)
                    V_grid[j][M] = 0
            
            # Interpolate to find option value at current spot
            i = int(S / dS)
            if i >= M:
                return V_grid[0][M]
            elif i <= 0:
                return V_grid[0][0]
            else:
                # Linear interpolation
                weight = (S - S_grid[i]) / dS
                return (1 - weight) * V_grid[0][i] + weight * V_grid[0][i + 1]

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)