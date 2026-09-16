import math
from typing import Optional, Callable

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionHestonSLVPriceFactor(CompanyShareOptionFactor):
    """
    Heston Stochastic Local Volatility (Heston-SLV) price factor for company share options.

    The Heston-SLV model combines a stochastic variance process with a local
    volatility leverage function L(S, t) so that the model exactly reproduces
    the market-implied local-volatility surface in expectation:

        dS_t = (r-q) S_t dt  +  L(S_t, t) sqrt(v_t) S_t dW_t^S
        dv_t = kappa(theta - v_t) dt  +  xi sqrt(v_t) dW_t^v
        corr(dW^S, dW^v) = rho

    where  L(S,t) = sigma_local(S,t) / sqrt(E[v_t | S_t=S])

    This is a thin domain factor.  Heavy numerical work is delegated to the
    Heston-SLV service layer:
        src.application.services.data.entities.factor.heston_slv

    Two usage modes
    ---------------
    1. Direct mode (fast, via service layer):
       Call calculate() with a pre-built HestonSLVModel injected via
       set_model() or by constructing this factor with model=...

    2. MC estimation (pure stdlib, slower):
       Call calculate() without a service-layer model.  In this case the
       factor runs a simplified Monte Carlo using only the stdlib math/random
       modules (no numpy/scipy required in the domain layer).
    """

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        model=None,   # optional pre-calibrated HestonSLVModel (service layer)
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
        self._model = model

    def set_model(self, model) -> None:
        """Inject a calibrated HestonSLVModel for pricing."""
        self._model = model

    # ------------------------------------------------------------------ #
    #  Primary pricing entry point                                          #
    # ------------------------------------------------------------------ #

    def calculate(
        self,
        S: float,                # underlying spot price
        K: float,                # option strike
        r: float,                # risk-free rate (continuous)
        T: float,                # time to maturity in years
        v0: float,               # initial variance (sigma^2, not sigma)
        kappa: float,            # mean-reversion speed
        theta: float,            # long-run variance
        xi: float,               # vol-of-vol
        rho: float,              # spot-vol correlation
        q: float = 0.0,          # continuous dividend yield
        option_type: str = "call",
        n_paths: int = 10_000,   # MC paths (used in stdlib fallback or service call)
        n_steps: int = 252,      # time steps
        local_vol_func: Optional[Callable[[float, float], float]] = None,
        leverage_func: Optional[Callable[[float, float], float]] = None,
    ) -> Optional[float]:
        """
        Calculate the Heston-SLV option price.

        If a calibrated HestonSLVModel has been injected, delegates to the
        service layer (vectorized numpy MC).

        Otherwise falls back to a simplified stdlib Monte Carlo that
        uses a leverage function if provided, or pure Heston if not.

        Parameters
        ----------
        local_vol_func  : callable sigma_loc(S, t) → float, used by the
                          service layer for leverage calibration (ignored here)
        leverage_func   : callable L(S, t) → float used in the stdlib MC
                          (defaults to L=1 when None, giving pure Heston dynamics)
        """
        if S <= 0 or K <= 0 or T <= 0 or v0 <= 0:
            return None
        if kappa <= 0 or theta <= 0 or xi <= 0:
            return None
        if abs(rho) >= 1.0:
            return None

        # ── Service layer path ────────────────────────────────────────── #
        if self._model is not None:
            try:
                return self._model.price(S, K, T, option_type, n_paths, n_steps)
            except Exception:
                pass

        # ── stdlib Monte Carlo fallback ───────────────────────────────── #
        return self._calculate_stdlib_mc(
            S, K, r, T, v0, kappa, theta, xi, rho, q,
            option_type, n_paths, n_steps, leverage_func,
        )

    # ------------------------------------------------------------------ #
    #  Stdlib Monte Carlo fallback (no numpy/scipy in domain layer)         #
    # ------------------------------------------------------------------ #

    def _calculate_stdlib_mc(
        self,
        S: float, K: float, r: float, T: float,
        v0: float, kappa: float, theta: float, xi: float, rho: float,
        q: float, option_type: str, n_paths: int, n_steps: int,
        leverage_func: Optional[Callable[[float, float], float]],
    ) -> Optional[float]:
        """
        Heston-SLV Monte Carlo using only Python stdlib (math + random).
        Full Truncation Euler scheme.  Leverage function L(S, t) defaults to 1.
        """
        import random

        try:
            dt     = T / n_steps
            sqrt_dt = math.sqrt(dt)
            rho_perp = math.sqrt(max(1.0 - rho * rho, 0.0))
            discount = math.exp(-r * T)

            payoff_sum = 0.0

            for _ in range(n_paths):
                S_t = S
                v_t = v0

                for step in range(n_steps):
                    t_now = step * dt

                    z1 = random.gauss(0.0, 1.0)
                    z2 = random.gauss(0.0, 1.0)
                    z_v = rho * z1 + rho_perp * z2

                    v_plus  = max(v_t, 0.0)
                    sqrt_v  = math.sqrt(v_plus)

                    # Leverage function (default L=1 → pure Heston)
                    L = leverage_func(S_t, t_now) if leverage_func is not None else 1.0
                    L = max(L, 0.0)

                    vol_eff = L * sqrt_v

                    # Log-Euler spot update
                    S_t = S_t * math.exp(
                        (r - q - 0.5 * vol_eff * vol_eff) * dt
                        + vol_eff * sqrt_dt * z1
                    )
                    S_t = max(S_t, 1e-10)

                    # Full Truncation Euler variance
                    v_t = v_t + kappa * (theta - v_plus) * dt + xi * sqrt_v * sqrt_dt * z_v
                    v_t = max(v_t, 0.0)

                if option_type.lower() == "call":
                    payoff_sum += max(S_t - K, 0.0)
                else:
                    payoff_sum += max(K - S_t, 0.0)

            return discount * payoff_sum / n_paths

        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    # ------------------------------------------------------------------ #
    #  Heston-only helpers (comparable to existing HestonPriceFactor)       #
    # ------------------------------------------------------------------ #

    def feller_condition_check(self, kappa: float, theta: float, xi: float) -> bool:
        """True when 2*kappa*theta >= xi^2 (variance stays strictly positive)."""
        return 2.0 * kappa * theta >= xi * xi

    def local_vol_from_leverage(
        self,
        leverage_func: Callable[[float, float], float],
        S: float,
        t: float,
        cond_var: float,
    ) -> float:
        """
        Recover local vol from leverage and conditional variance:
            sigma_loc = L(S, t) * sqrt(E[v_t | S_t=S])
        """
        if cond_var <= 0:
            return 0.0
        return leverage_func(S, t) * math.sqrt(cond_var)
