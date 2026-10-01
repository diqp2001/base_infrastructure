

from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import CompanyShareOptionValueFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_factor import CompanyShareOptionPriceFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import CompanyShareOptionImpliedVolFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import CompanyShareOptionImpliedVolMlFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_div_yield_factor import CompanyShareOptionImpliedDivYieldFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import CompanyShareOptionRFYieldFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_corr_factor import CompanyShareOptionImpliedCorrFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor import CompanyShareOptionDeltaFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import CompanyShareOptionGammaFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor import CompanyShareOptionVegaFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vol_factor import CompanyShareOptionVolFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_var_factor import CompanyShareOptionVarFactor

# Pricing model factors
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import CompanyShareOptionBlackScholesMertonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_cox_ross_rubinstein_price_factor import CompanyShareOptionCoxRossRubinsteinPriceFactor 
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor import CompanyShareOptionHestonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_hull_white_price_factor import CompanyShareOptionHullWhitePriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_sabr_price_factor import CompanyShareOptionSABRPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_bates_price_factor import CompanyShareOptionBatesPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_dupire_local_volatility_price_factor import CompanyShareOptionDupireLocalVolatilityPriceFactor


COMPANY_SHARE_OPTION_LIBRARY: Dict[str, Dict] = {
    
    "open": {
        "class": CompanyShareOptionFactor, 
        "name": "open",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level open price",
        "dependencies": [],
        "parameters": {}
    },
    "high": {
        "class": CompanyShareOptionFactor, 
        "name": "high",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level high price",
        "dependencies": [],
        "parameters": {}
    },
    "low": {
        "class": CompanyShareOptionFactor, 
        "name": "low",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level low price",
        "dependencies": [],
        "parameters": {}
    },
    "close": {
        "class": CompanyShareOptionFactor, 
        "name": "close",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level close price",
        "dependencies": [],
        "parameters": {}
    },
    "volume": {
        "class": CompanyShareOptionFactor, 
        "name": "volume",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },
    "implied_volatility": {
            "class": CompanyShareOptionFactor,
            "name": "implied_volatility",
            "group": "volatility",
            "subgroup": "implied",
            "frequency": "1d",
            "data_type": "numeric",
            "description": "Minute-level implied volatility",
            "source": "ibkr",
            "dependencies": [],
            "parameters": {}
        },

    "implied_volatility_calculated": {
                "class": CompanyShareOptionImpliedVolFactor,
                "name": "implied_volatility_calculated",
                "group": "volatility",
                "subgroup": "implied",
                "frequency": "1d",
                "data_type": "numeric",
                "description": "Minute-level implied volatility",
                "source": "calculated",
                "dependencies": [],
                "parameters": {}
            },

            "implied_vol_ml": {
                    "class": CompanyShareOptionImpliedVolMlFactor,
                    "name": "implied_vol_ml",
                    "group": "volatility",
                    "subgroup": "implied",
                    "frequency": "1d",
                    "data_type": "numeric",
                    "source": "calculated",
                    "description": "ML-predicted implied volatility of a company share option; trained on analytical implied vol values; auto-trains on regime change",
                    "dependencies": {},
                    "parameters": {}
                },

    "rf_yield": {
        "class": CompanyShareOptionRFYieldFactor,
        "name": "rf_yield",
        "group": "fundamental",
        "subgroup": "yield",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "Risk-free overnight repo yield derived from the option currency's CurrencyYieldFactor (SOFR, ESTR, SONIA, etc.)",
        "dependencies": {
           
        },
        "parameters": {}
    },
    "company_share_option_value": {
        "class": CompanyShareOptionValueFactor,
        "name": "company_share_option_value",
        "group": "value",
                "subgroup": "asset",
                "frequency": "1d",
                "data_type": "decimal",
        
        "description": "Option price ",
        
        "parameters": {}
    },

    "return_open": {
        "class": CompanyShareOptionPriceReturnFactor,
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        
        "parameters": {}
    },

    # Daily return factors
    "return_daily": {
        "class": CompanyShareOptionPriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        
        "parameters": {"period": "1D"}
    },
    
    "implied_vol": {
        "class": CompanyShareOptionImpliedVolFactor,
        "name": "implied_vol",
        "group": "volatility",
        "subgroup": "implied",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Implied volatility of a single company share option via Newton-Raphson B-S inversion; depends on CompanyShareOptionFactor price from IBKR",
        "dependencies": {},
        "parameters": {}
    },

    

    "delta": {
        "class": CompanyShareOptionDeltaFactor,
        "name": "delta",
        "group": "greek",
        "subgroup": "delta",
        "frequency": "1d",
        "data_type": "numeric",
        "source": "calculated",
        "description": "BSM delta (∂V/∂S) of a company share option; depends on CompanyShareValueFactor (S), CompanyShareOptionImpliedVolFactor (σ), CompanyShareOptionRFYieldFactor (r)",
        "dependencies": {},
        "parameters": {}
    },

    "gamma": {
        "class": CompanyShareOptionGammaFactor,
        "name": "gamma",
        "group": "greek",
        "subgroup": "gamma",
        "frequency": "1d",
        "data_type": "numeric",
        "source": "calculated",
        "description": "BSM gamma (∂²V/∂S²) of a company share option; same dependency chain as delta: S, σ, r",
        "dependencies": {},
        "parameters": {}
    },

    "vega": {
        "class": CompanyShareOptionVegaFactor,
        "name": "vega",
        "group": "greek",
        "subgroup": "vega",
        "frequency": "1d",
        "data_type": "numeric",
        "source": "calculated",
        "description": "BSM vega (∂V/∂σ) of a company share option; same dependency chain as delta/gamma: S, σ, r",
        "dependencies": {},
        "parameters": {}
    },

    "implied_div_yield": {
        "class": CompanyShareOptionImpliedDivYieldFactor,
        "name": "implied_div_yield",
        "group": "fundamental",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Implied dividend yield of a company share derived from put-call parity; depends on CompanyShareOptionFactor price from IBKR",
        "dependencies": {},
        "parameters": {}
    },

    "implied_corr": {
        "class": CompanyShareOptionImpliedCorrFactor,
        "name": "implied_corr",
        "group": "volatility",
        "subgroup": "implied",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Implied correlation across correlated underlyings derived from option vol surface; depends on CompanyShareOptionFactor price from IBKR; returns None until cross-asset vol surface is integrated",
        "dependencies": {},
        "parameters": {}
    },

    "vol": {
        "class": CompanyShareOptionVolFactor,
        "name": "vol",
        "group": "volatility",
        "subgroup": "realized",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Annualised realised volatility of option price series (std of log-returns * sqrt(252)); depends on CompanyShareOptionFactor price series from IBKR",
        "dependencies": {},
        "parameters": {}
    },

    "var": {
        "class": CompanyShareOptionVarFactor,
        "name": "var",
        "group": "volatility",
        "subgroup": "realized",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Annualised realised variance of option price series (var of log-returns * 252); depends on CompanyShareOptionFactor price series from IBKR",
        "dependencies": {},
        "parameters": {}
    },

    # Advanced Pricing Model Factors
    "black_scholes_merton_price": {
        "class": CompanyShareOptionBlackScholesMertonPriceFactor,
        "name": "black_scholes_merton_price",
        "group": "price_model",
        "subgroup": "black_scholes",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Black-Scholes-Merton option price with dividend yield",
        
        "parameters": {}
    },

    "cox_ross_rubinstein_price": {
        "class": CompanyShareOptionCoxRossRubinsteinPriceFactor,
        "name": "cox_ross_rubinstein_price",
        "group": "price_model",
        "subgroup": "binomial_tree",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Cox-Ross-Rubinstein binomial tree option price",
        
        "parameters": {"tree_steps": 100}
    },

    "heston_price": {
        "class": CompanyShareOptionHestonPriceFactor,
        "name": "heston_price",
        "group": "price_model",
        "subgroup": "stochastic_volatility",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Heston stochastic volatility option price",
        
        "parameters": {"monte_carlo_paths": 10000}
    },

    "hull_white_price": {
        "class": CompanyShareOptionHullWhitePriceFactor,
        "name": "hull_white_price",
        "group": "price_model",
        "subgroup": "stochastic_rates",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Hull-White stochastic interest rate option price",
        
        "parameters": {}
    },

    "sabr_price": {
        "class": CompanyShareOptionSABRPriceFactor,
        "name": "sabr_price",
        "group": "price_model",
        "subgroup": "sabr",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "SABR model option price with volatility smile",
        
        "parameters": {}
    },

    "bates_price": {
        "class": CompanyShareOptionBatesPriceFactor,
        "name": "bates_price",
        "group": "price_model",
        "subgroup": "jump_diffusion",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Bates jump-diffusion option price",
        
        "parameters": {"monte_carlo_paths": 10000}
    },

    "dupire_local_volatility_price": {
        "class": CompanyShareOptionDupireLocalVolatilityPriceFactor,
        "name": "dupire_local_volatility_price",
        "group": "price_model",
        "subgroup": "local_volatility",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Dupire local volatility option price",
        
        "parameters": {"grid_size": 100}
    },
    
}