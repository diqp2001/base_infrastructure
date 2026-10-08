"""
Heston-SLV calibration example.

Demonstrates the full workflow on a synthetic implied-volatility surface
generated from known Heston parameters:

    Step 1  Generate synthetic market IV surface (known Heston params)
    Step 2  Calibrate Heston model to the surface
    Step 3  Build Dupire local-vol surface
    Step 4  Run iterative SLV calibration (fixed-point leverage)
    Step 5  Compare market IV vs Heston IV vs SLV IV across strikes

Run from the repository root:
    python -m src.application.services.data.entities.factor.heston_slv.examples.heston_slv_example
"""

from __future__ import annotations

import math

import numpy as np

from src.application.services.data.entities.factor.heston_slv.heston_slv_parameters import (
    HestonParameters,
)
from src.application.services.data.entities.factor.heston_slv.heston_pricer import HestonPricer
from src.application.services.data.entities.factor.heston_slv.heston_calibrator import HestonCalibrator
from src.application.services.data.entities.factor.heston_slv.implied_vol_surface import (
    ImpliedVolatilitySurface,
    OptionPriceSurface,
    MarketQuote,
)
from src.application.services.data.entities.factor.heston_slv.dupire_local_vol import (
    DupireLocalVolatility,
)
from src.application.services.data.entities.factor.heston_slv.heston_slv_model import (
    HestonSLVCalibrator,
    HestonSLVConfig,
)


# ─────────────────────────────────────────────────────────────────────────── #
#  1. True parameters (used to generate synthetic market quotes)               #
# ─────────────────────────────────────────────────────────────────────────── #

TRUE_PARAMS = HestonParameters(
    v0=0.04, kappa=1.5, theta=0.04, xi=0.35, rho=-0.6,
    r=0.05, q=0.01
)
S0 = 100.0

pricer = HestonPricer()

print("=" * 65)
print("Heston-SLV Example")
print("=" * 65)
print(f"\nTrue parameters: {TRUE_PARAMS}")
print(f"Feller condition satisfied: {TRUE_PARAMS.feller_condition()}")

# ─────────────────────────────────────────────────────────────────────────── #
#  2. Generate synthetic market quotes                                          #
# ─────────────────────────────────────────────────────────────────────────── #

strikes    = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
maturities = [0.25, 0.5, 1.0, 1.5, 2.0]

quotes = []
for T in maturities:
    for K in strikes:
        iv = pricer.implied_vol(S0, K, T, TRUE_PARAMS)
        if iv is not None:
            quotes.append(MarketQuote(strike=K, maturity=T, iv=iv, weight=1.0))

print(f"\nGenerated {len(quotes)} synthetic quotes.")

# ─────────────────────────────────────────────────────────────────────────── #
#  3. Calibrate Heston model                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

print("\n─── Calibrating Heston model ───")
iv_surface = ImpliedVolatilitySurface(quotes, S0, r=TRUE_PARAMS.r, q=TRUE_PARAMS.q)

market_ivs = np.array([
    [iv_surface.iv(K, T) for T in maturities]
    for K in strikes
])

cal = HestonCalibrator(pricer)
calibrated = cal.calibrate(
    strikes, maturities, market_ivs, S0,
    r=TRUE_PARAMS.r, q=TRUE_PARAMS.q,
    use_global_search=True, seed=0,
)
print(f"Calibrated: {calibrated}")

# ─────────────────────────────────────────────────────────────────────────── #
#  4. Heston calibration quality                                                #
# ─────────────────────────────────────────────────────────────────────────── #

print(f"\n{'Strike':>8}  {'T':>5}  {'Market IV':>10}  {'Heston IV':>10}  {'Error bps':>10}")
print("-" * 50)
for T in [0.5, 1.0]:
    for K in [90.0, 100.0, 110.0]:
        miv = iv_surface.iv(K, T)
        hiv = pricer.implied_vol(S0, K, T, calibrated)
        err = (hiv - miv) * 1e4 if hiv else float("nan")
        print(f"  {K:6.1f}  {T:5.2f}  {miv:10.4f}  {hiv or 0:10.4f}  {err:10.1f}")

# ─────────────────────────────────────────────────────────────────────────── #
#  5. Dupire local-vol surface                                                  #
# ─────────────────────────────────────────────────────────────────────────── #

print("\n─── Building Dupire local-vol surface ───")
K_grid = np.linspace(80.0, 120.0, 20)
T_grid = np.linspace(0.1, 2.0, 15)
price_surface = OptionPriceSurface(iv_surface, K_grid, T_grid)
lv_surface    = DupireLocalVolatility().calibrate(price_surface)

print(f"  ATM (K=100, T=1): sigma_loc = {lv_surface(100.0, 1.0):.4f}")
print(f"  OTM call (K=110, T=1): sigma_loc = {lv_surface(110.0, 1.0):.4f}")
print(f"  OTM put  (K=90,  T=1): sigma_loc = {lv_surface(90.0, 1.0):.4f}")

# ─────────────────────────────────────────────────────────────────────────── #
#  6. Iterative SLV calibration                                                 #
# ─────────────────────────────────────────────────────────────────────────── #

print("\n─── Running iterative SLV calibration ───")
slv_config = HestonSLVConfig(
    max_iter        = 3,
    n_particles     = 3_000,
    n_steps_per_year= 52,
    n_spot_grid     = 20,
    n_time_grid     = 10,
    relax_alpha     = 0.8,
    smooth_sigma    = 1.0,
    seed            = 42,
)
slv_calibrator = HestonSLVCalibrator()
slv_model = slv_calibrator.calibrate(
    quotes, S0,
    r=TRUE_PARAMS.r, q=TRUE_PARAMS.q,
    config=slv_config,
    heston_params=calibrated,   # reuse Heston calibration
)
print(f"Converged: {slv_model.converged}  |  Iterations: {slv_model.n_iterations}")
if slv_model.diagnostics:
    print(f"ΔL convergence: {[f'{d:.5f}' for d in slv_model.diagnostics]}")

# ─────────────────────────────────────────────────────────────────────────── #
#  7. Compare market IV vs Heston IV vs SLV IV                                 #
# ─────────────────────────────────────────────────────────────────────────── #

print(f"\n{'Strike':>8}  {'Market IV':>10}  {'Heston IV':>10}  {'SLV IV':>10}")
print("-" * 46)
T_eval = 1.0
for K in [90.0, 95.0, 100.0, 105.0, 110.0]:
    miv  = iv_surface.iv(K, T_eval)
    hiv  = pricer.implied_vol(S0, K, T_eval, calibrated) or float("nan")
    slv_iv = slv_model.implied_vol(
        S0, K, T_eval, n_paths=10_000, n_steps=100, seed=int(K)
    ) or float("nan")
    print(f"  {K:6.1f}  {miv:10.4f}  {hiv:10.4f}  {slv_iv:10.4f}")

print("\nDone.")
