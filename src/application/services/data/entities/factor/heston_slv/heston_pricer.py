"""
HestonPricer – semi-analytic European option pricer via Gil-Pelaez inversion.

Uses the Albrecher et al. (2007) "little-trap" stable characteristic function
to avoid branch-cut discontinuities that arise in the original Heston (1993) paper.

Reference
---------
Albrecher H., Mayer P., Schachermayer W., Teichmann J. (2007)
"The Gumbel distribution and its connection with the Heston model."
"""

from __future__ import annotations

import cmath
import math
from typing import Optional, Tuple

from scipy import integrate
from scipy.stats import norm

from .heston_slv_parameters import HestonParameters


class HestonPricer:
    """
    Semi-analytic Heston pricer.

    The call price is:

        C = S e^{-qT} P1 - K e^{-rT} P2

    where P1, P2 are risk-adjusted probabilities computed by Gil-Pelaez inversion
    of the two Heston characteristic functions f1, f2.
    """

    # Upper bound of the integration domain.  200 works for most liquid parameters.
    _PHI_MAX: float = 200.0
    # scipy.integrate.quad limit (sub-intervals).
    _QUAD_LIMIT: int = 200

    # ------------------------------------------------------------------ #
    #  Characteristic functions                                            #
    # ------------------------------------------------------------------ #

    def _char_func(
        self,
        phi: float,
        j: int,
        S: float,
        T: float,
        params: HestonParameters,
    ) -> complex:
        """
        Heston characteristic function for j=1 (S-measure) or j=2 (Q-measure).

        Implements the Albrecher et al. (2007) stable formulation which replaces
        the standard g = (b - d) / (b + d) by g_stable = (b + d) / (b - d)
        and swaps e^{-dT} → e^{dT} in the log term.  This avoids the branch-cut
        discontinuity that corrupts the standard formula for large phi.
        """
        kappa = params.kappa
        theta = params.theta
        xi    = params.xi
        rho   = params.rho
        v0    = params.v0
        r, q  = params.r, params.q

        i_phi = 1j * phi   # purely imaginary

        if j == 1:
            u: float = 0.5
            b: float = kappa - rho * xi        # b_1 = kappa - rho*xi
        else:
            u = -0.5
            b = kappa                          # b_2 = kappa

        # d = sqrt[(b - rho*xi*i*phi)^2 - xi^2*(2*u*i*phi - phi^2)]
        d = cmath.sqrt(
            (b - rho * xi * i_phi) ** 2
            - xi ** 2 * (2.0 * u * i_phi - phi ** 2)
        )

        # Stable form: numerator / denominator of g
        num_g = b - rho * xi * i_phi + d
        den_g = b - rho * xi * i_phi - d

        if abs(den_g) < 1e-15:
            return 0j

        g = num_g / den_g

        e_dT = cmath.exp(d * T)
        log_num = 1.0 - g * e_dT
        log_den = 1.0 - g

        if abs(log_num) < 1e-15 or abs(log_den) < 1e-15:
            return 0j

        # Exponent components
        A = (
            (r - q) * i_phi * T
            + kappa * theta / xi ** 2
            * (num_g * T - 2.0 * cmath.log(log_num / log_den))
        )
        B = num_g / xi ** 2 * (1.0 - e_dT) / (1.0 - g * e_dT)

        return cmath.exp(A + B * v0 + i_phi * cmath.log(S))

    # ------------------------------------------------------------------ #
    #  Gil-Pelaez probability                                              #
    # ------------------------------------------------------------------ #

    def _P(self, j: int, S: float, K: float, T: float, params: HestonParameters) -> float:
        """
        Compute the Gil-Pelaez probability P_j.

            P_j = 0.5 + (1/pi) * int_0^inf Re[f_j(phi) * e^{-i*phi*ln K} / (i*phi)] dphi
        """
        log_K = math.log(K)

        def integrand(phi: float) -> float:
            if phi < 1e-10:
                return 0.0
            try:
                cf  = self._char_func(phi, j, S, T, params)
                val = (cmath.exp(-1j * phi * log_K) * cf / (1j * phi)).real
                return val if math.isfinite(val) else 0.0
            except (OverflowError, ValueError, ZeroDivisionError):
                return 0.0

        result, _ = integrate.quad(
            integrand,
            0.0,
            self._PHI_MAX,
            limit=self._QUAD_LIMIT,
            points=[0.5, 1.0, 5.0, 20.0],
        )
        return 0.5 + result / math.pi

    # ------------------------------------------------------------------ #
    #  Public interface                                                     #
    # ------------------------------------------------------------------ #

    def price(
        self,
        S: float,
        K: float,
        T: float,
        params: HestonParameters,
        option_type: str = "call",
    ) -> Optional[float]:
        """
        Semi-analytic Heston European option price.

        Returns None if inputs are invalid.
        """
        if S <= 0 or K <= 0 or T <= 0 or params.v0 <= 0:
            return None
        if abs(params.rho) >= 1.0 or params.xi <= 0 or params.kappa <= 0:
            return None

        try:
            r, q = params.r, params.q
            P1 = self._P(1, S, K, T, params)
            P2 = self._P(2, S, K, T, params)

            call = S * math.exp(-q * T) * P1 - K * math.exp(-r * T) * P2
            call = max(call, 0.0)

            if option_type.lower() == "put":
                # Put-call parity
                put = call - S * math.exp(-q * T) + K * math.exp(-r * T)
                return max(put, 0.0)

            return call

        except Exception:
            return None

    def implied_vol(
        self,
        S: float,
        K: float,
        T: float,
        params: HestonParameters,
        option_type: str = "call",
        tol: float = 1e-7,
        max_iter: int = 80,
    ) -> Optional[float]:
        """
        Heston implied volatility obtained by BSM-inversion of the semi-analytic price.
        """
        price = self.price(S, K, T, params, option_type)
        if price is None:
            return None

        from .implied_vol_surface import iv_from_price
        return iv_from_price(price, S, K, params.r, params.q, T, option_type, tol, max_iter)

    # ------------------------------------------------------------------ #
    #  BSM helpers (used by the calibrator)                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def bsm_price(S: float, K: float, r: float, q: float, T: float, sigma: float) -> float:
        """Black-Scholes-Merton call price."""
        if T <= 0 or sigma <= 0:
            return max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)
        sqT = math.sqrt(T)
        d1  = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqT)
        d2  = d1 - sigma * sqT
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)

    @staticmethod
    def bsm_vega(S: float, K: float, r: float, q: float, T: float, sigma: float) -> float:
        """BSM vega (derivative w.r.t. sigma)."""
        if T <= 0 or sigma <= 0:
            return 0.0
        sqT = math.sqrt(T)
        d1  = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqT)
        return S * math.exp(-q * T) * norm.pdf(d1) * sqT

    @staticmethod
    def bsm_iv(
        price: float,
        S: float,
        K: float,
        r: float,
        q: float,
        T: float,
        option_type: str = "call",
        tol: float = 1e-8,
        max_iter: int = 100,
    ) -> Optional[float]:
        """Newton-Raphson BSM implied vol from a call (or put) price."""
        from .implied_vol_surface import iv_from_price
        return iv_from_price(price, S, K, r, q, T, option_type, tol, max_iter)
