"""
Regime-Switched No-Trade-Band Delta Rebalancing
================================================

This module provides two closed-form no-trade band (NTB) models for delta
hedging options portfolios under proportional transaction costs, and a
regime-dispatching wrapper that selects between them.

TWO MODELS
----------

Model 1 — Whalley and Wilmott (1997)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Source: Whalley, A.E. & Wilmott, P. (1997). "An Asymptotic Analysis of an
  Optimal Hedging Model for Option Pricing with Transaction Costs."
  Mathematical Finance, 7(3), 307–324.

Utility framework: CARA (Constant Absolute Risk Aversion)
  u(W) = -exp(-a · W),  a > 0

Transaction cost: proportional to the dollar value of each hedge trade
  cost = k · S · |Δ_change|,  k = fractional cost rate (e.g. 0.001 = 10 bps)

Derivation: asymptotic perturbation expansion in ε = k^{1/3} → 0, leading
  to a no-trade band whose half-width (in delta units) is:

    H_WW = [ (3/2) · (k · S / a) · exp(r · τ) · |Γ| ]^{1/3}        (WW 1997, §3)

  k   = cost_rate         (proportional transaction cost fraction)
  S   = spot              (underlying spot price)
  a   = risk_aversion     (CARA coefficient; see Calibration below)
  τ   = time_to_expiry    (years remaining)
  r   = risk_free_rate    (continuously compounded, default 0.05)
  Γ   = |gamma|           (|∂²V/∂S²| of the option or spread portfolio)

The no-trade region is [Δ_BS − H_WW, Δ_BS + H_WW].  When the current hedge
delta exits this region, the trader moves to the band edge (not to exact
neutrality) to avoid immediately re-triggering the threshold.

Limitations:
  • Valid asymptotically for small k; may over-estimate the band for large k.
  • Does not depend on σ explicitly — assumes stable volatility.
  • Best suited to normal / low-volatility regimes.


Model 2 — Zakamouline (2009)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Source: Zakamouline, V.I. (2009). "Optimal Hedging of Options with
  Transaction Costs." Journal of Economic Dynamics and Control, 33(5),
  967–997.

Same CARA utility and proportional cost structure as WW, but solves the
EXACT optimal control problem rather than an asymptotic approximation.
The closed-form result incorporates local / implied volatility explicitly:

    H_Z = sqrt[ (k · S · exp(r · τ) · |Γ|) / (a · σ²) ]            (Zakamouline 2009, Thm 2)

  σ   = implied_vol   (ATM implied or local volatility, annualised)

All other symbols as in WW above.

Key differences from WW:
  • Scales as k^{1/2} and |Γ|^{1/2}  (vs WW's k^{1/3}, |Γ|^{1/3}).
  • σ in denominator: higher vol → narrower band (more frequent rebalancing),
    because large gamma P&L swings are amplified by volatility and tighter
    tracking reduces the expected hedging loss.
  • More capital-efficient than WW for the same risk-aversion level when
    volatility is high.

Crossover: the two models agree when σ² = (2/3) · H_WW.  For typical SPX
  parameters (H_WW ≈ 0.051), crossover is near σ ≈ 18.4%.  Above that:
  H_Z < H_WW (Zakamouline tighter); below it: H_Z > H_WW (WW tighter).

Limitations:
  • CARA utility may not match a leveraged desk's actual risk preference.
  • σ is treated as constant; recalibrate when vol regime shifts.


REGIME DISPATCH
---------------
compute_hedge_band() selects the model based on the current market regime
(set by Strategy.analyze_market_conditions()):

  Default mapping (overridable via regime_map kwarg):
    'high_volatility'  →  zakamouline   (exact, vol-aware, tighter bands)
    'normal'           →  whalley_wilmott
    'low_volatility'   →  whalley_wilmott


CALIBRATION OF risk_aversion (a)
---------------------------------
Both formulas treat `a` as a dimensionless tuning parameter that must be
calibrated against the trader's actual risk appetite via backtesting.

For SPX call-spread market making (S≈4500, |Γ|≈2×10⁻⁴, k≈10⁻⁴, τ≈0.1yr):
  a = 1.0  →  H_WW ≈ 0.051, H_Z ≈ 0.048  (σ=0.20)
  a = 2.0  →  H_WW ≈ 0.041, H_Z ≈ 0.034  (σ=0.20)

Recommended backtest targets:
  • Average hedge frequency ≈ 1–2×/week per position (cost vs. tracking tradeoff)
  • Transaction-cost drag < 20 bps/month for the hedging book
  • sigma(a) sensitivity: stress-test with a ± 50% around the calibrated value

Strategy config keys (consumed by Strategy.evaluate_delta_hedge):
  'hedge_transaction_cost_rate'  float  default 0.0001
  'hedge_risk_aversion'          float  default 1.0      ← needs calibration
  'hedge_band_regime_map'        dict   default see above
"""

import math
from typing import Any, Dict, Optional

_DEFAULT_REGIME_MAP: Dict[str, str] = {
    'high_volatility': 'zakamouline',
    'normal': 'whalley_wilmott',
    'low_volatility': 'whalley_wilmott',
}

# Cost-rate threshold above which WW-NTBN is preferred regardless of vol regime.
_DEFAULT_COST_HIGH_THRESHOLD: float = 0.005


def select_hedge_method(
    regime: str,
    cost_rate: float,
    cost_high_threshold: float = _DEFAULT_COST_HIGH_THRESHOLD,
) -> str:
    """Select hedging model based on market regime and transaction-cost level.

    Three-way dispatch:
      low_volatility  AND  low cost  →  'whalley_wilmott'  (asymptotic, fast)
      normal                         →  'zakamouline'      (exact, vol-aware)
      high_volatility  OR  high cost →  'ww_ntbn'          (data-driven residual)

    "High cost" is defined as cost_rate >= cost_high_threshold.

    Args:
        regime: Market regime string, typically one of 'low_volatility',
            'normal', 'high_volatility'.
        cost_rate: Proportional transaction cost fraction k.
        cost_high_threshold: Threshold above which cost is considered high.
            Default 0.005 (50 bps).

    Returns:
        One of 'whalley_wilmott', 'zakamouline', 'ww_ntbn'.
    """
    high_cost = cost_rate >= cost_high_threshold
    if regime == 'high_volatility' or high_cost:
        return 'ww_ntbn'
    elif regime == 'low_volatility':
        return 'whalley_wilmott'
    else:
        return 'zakamouline'


def whalley_wilmott_band(
    gamma: float,
    spot: float,
    cost_rate: float,
    risk_aversion: float,
    **kwargs: Any,
) -> float:
    """No-trade half-band in delta units using Whalley-Wilmott (1997).

    Formula: H_WW = [(3/2) · (k·S/a) · exp(r·τ) · |Γ|]^{1/3}

    Args:
        gamma: Portfolio gamma ∂²V/∂S²; sign is ignored (absolute value used).
        spot: Underlying spot price S (> 0).
        cost_rate: Proportional transaction cost fraction k (> 0).
        risk_aversion: CARA risk-aversion coefficient a (> 0).
        **kwargs:
            time_to_expiry (float): Years to expiry τ. Default 1/52.
            risk_free_rate (float): Continuously compounded risk-free rate r. Default 0.05.

    Returns:
        Half-width of the no-trade band in delta units (≥ 0).

    Raises:
        ValueError: If cost_rate ≤ 0, risk_aversion ≤ 0, or spot ≤ 0.
    """
    if cost_rate <= 0:
        raise ValueError(f"cost_rate must be > 0, got {cost_rate}")
    if risk_aversion <= 0:
        raise ValueError(f"risk_aversion must be > 0, got {risk_aversion}")
    if spot <= 0:
        raise ValueError(f"spot must be > 0, got {spot}")

    abs_gamma = abs(gamma)
    if abs_gamma == 0.0:
        return 0.0

    tau = float(kwargs.get('time_to_expiry', 1.0 / 52.0))
    r = float(kwargs.get('risk_free_rate', 0.05))

    inner = (3.0 / 2.0) * (cost_rate * spot / risk_aversion) * math.exp(r * tau) * abs_gamma
    return inner ** (1.0 / 3.0)


def zakamouline_band(
    gamma: float,
    spot: float,
    cost_rate: float,
    risk_aversion: float,
    **kwargs: Any,
) -> float:
    """No-trade half-band in delta units using Zakamouline (2009).

    Formula: H_Z = sqrt[(k·S·exp(r·τ)·|Γ|) / (a·σ²)]

    Args:
        gamma: Portfolio gamma ∂²V/∂S²; sign is ignored.
        spot: Underlying spot price S (> 0).
        cost_rate: Proportional transaction cost fraction k (> 0).
        risk_aversion: CARA risk-aversion coefficient a (> 0).
        **kwargs:
            implied_vol (float): ATM implied or local volatility σ (> 0). Default 0.20.
            time_to_expiry (float): Years to expiry τ. Default 1/52.
            risk_free_rate (float): Continuously compounded risk-free rate r. Default 0.05.

    Returns:
        Half-width of the no-trade band in delta units (≥ 0).

    Raises:
        ValueError: If cost_rate ≤ 0, risk_aversion ≤ 0, spot ≤ 0, or implied_vol ≤ 0.
    """
    if cost_rate <= 0:
        raise ValueError(f"cost_rate must be > 0, got {cost_rate}")
    if risk_aversion <= 0:
        raise ValueError(f"risk_aversion must be > 0, got {risk_aversion}")
    if spot <= 0:
        raise ValueError(f"spot must be > 0, got {spot}")

    sigma = float(kwargs.get('implied_vol', 0.20))
    if sigma <= 0:
        raise ValueError(f"implied_vol must be > 0 for Zakamouline band, got {sigma}")

    abs_gamma = abs(gamma)
    if abs_gamma == 0.0:
        return 0.0

    tau = float(kwargs.get('time_to_expiry', 1.0 / 52.0))
    r = float(kwargs.get('risk_free_rate', 0.05))

    inner = (cost_rate * spot * math.exp(r * tau) * abs_gamma) / (risk_aversion * sigma ** 2)
    return math.sqrt(inner)


def compute_hedge_band(
    gamma: float,
    spot: float,
    cost_rate: float,
    risk_aversion: float,
    regime: str = 'normal',
    **kwargs: Any,
) -> Dict[str, Any]:
    """Regime-dispatched no-trade band: selects WW or Zakamouline based on market regime.

    Always computes both models' values for diagnostics.

    Args:
        gamma: Portfolio gamma ∂²V/∂S²; sign is ignored.
        spot: Underlying spot price S (> 0).
        cost_rate: Proportional transaction cost fraction k (> 0).
        risk_aversion: CARA risk-aversion coefficient a (> 0).
        regime: Current market regime from Strategy.analyze_market_conditions().
            Typically 'normal', 'low_volatility', or 'high_volatility'.
        **kwargs:
            regime_map (dict): Override regime → model mapping. Merged with defaults
                {'high_volatility': 'zakamouline', 'normal': 'whalley_wilmott',
                 'low_volatility': 'whalley_wilmott'}.
            implied_vol (float): Required when Zakamouline is selected. Default 0.20.
            time_to_expiry (float): Years to expiry τ. Default 1/52.
            risk_free_rate (float): Risk-free rate r. Default 0.05.

    Returns:
        Dict with:
            half_width (float): Selected model's no-trade half-band in delta units.
            model_used (str): 'whalley_wilmott' or 'zakamouline'.
            regime (str): The regime used for dispatch.
            ww_half_width (float): Whalley-Wilmott half-band (always computed).
            zakamouline_half_width (float | None): Zakamouline half-band when sigma available.

    Raises:
        ValueError: If the selected model is Zakamouline and implied_vol is missing or ≤ 0.
    """
    regime_map = {**_DEFAULT_REGIME_MAP, **kwargs.pop('regime_map', {})}
    model_name = regime_map.get(regime, 'whalley_wilmott')

    ww_hw = whalley_wilmott_band(gamma, spot, cost_rate, risk_aversion, **kwargs)

    sigma = kwargs.get('implied_vol', None)
    zak_hw: Optional[float] = None
    if sigma is not None:
        try:
            zak_hw = zakamouline_band(gamma, spot, cost_rate, risk_aversion, **kwargs)
        except ValueError:
            zak_hw = None

    if model_name == 'zakamouline':
        if zak_hw is None:
            raise ValueError(
                f"Zakamouline model selected for regime '{regime}' but "
                f"implied_vol is missing or invalid."
            )
        half_width = zak_hw
    else:
        half_width = ww_hw

    return {
        'half_width': half_width,
        'model_used': model_name,
        'regime': regime,
        'ww_half_width': ww_hw,
        'zakamouline_half_width': zak_hw,
    }
