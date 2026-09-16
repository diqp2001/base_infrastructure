"""
Heston Stochastic Local Volatility (Heston-SLV) model service layer.

Components
----------
HestonParameters          -- parameter container
HestonPricer              -- semi-analytic pricing via characteristic function
HestonCalibrator          -- calibrate Heston params to market IV surface
HestonSimulator           -- numpy-vectorized Monte Carlo for Heston dynamics
ImpliedVolatilitySurface  -- market IV surface with smoothing / arb-free interp
OptionPriceSurface        -- smoothed call price surface with analytic derivatives
LocalVolatilitySurface    -- Dupire local-vol on a (K, T) grid
DupireLocalVolatility     -- compute Dupire surface from a smoothed price surface
ConditionalVarianceEstimator -- Gaussian-kernel E[v_t | S_t = S]
LeverageFunction          -- L(S, t) = sigma_loc / sqrt(E[v|S]) on a 2-D grid
HestonSLVModel            -- combines all components for pricing
HestonSLVCalibrator       -- iterative fixed-point SLV calibration
HestonSLVSimulator        -- numpy-vectorized SLV Monte Carlo
"""

from .heston_slv_parameters import HestonParameters
from .heston_pricer import HestonPricer
from .heston_calibrator import HestonCalibrator
from .heston_simulator import HestonSimulator
from .implied_vol_surface import ImpliedVolatilitySurface, OptionPriceSurface, MarketQuote
from .dupire_local_vol import LocalVolatilitySurface, DupireLocalVolatility
from .conditional_variance_estimator import ConditionalVarianceEstimator
from .leverage_function import LeverageFunction
from .heston_slv_model import HestonSLVModel, HestonSLVCalibrator, HestonSLVSimulator, HestonSLVConfig

__all__ = [
    "HestonParameters",
    "HestonPricer",
    "HestonCalibrator",
    "HestonSimulator",
    "MarketQuote",
    "ImpliedVolatilitySurface",
    "OptionPriceSurface",
    "LocalVolatilitySurface",
    "DupireLocalVolatility",
    "ConditionalVarianceEstimator",
    "LeverageFunction",
    "HestonSLVConfig",
    "HestonSLVModel",
    "HestonSLVCalibrator",
    "HestonSLVSimulator",
]
