

from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_factor import CompanyShareOptionPriceFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor

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
        "frequency": "1m",
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
        "frequency": "1m",
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
        "frequency": "1m",
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
        "frequency": "1m",
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
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },
    "option_price": {
        "class": CompanyShareOptionPriceFactor,
        "name": "option_price",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
                        "close": {
                    "class": CompanyShareFactor,
                    "name": "close",
                    "group": "price",
                    "subgroup": "minutes",
                    "frequency": "1m",
                    "data_type": "numeric",
                    "description": "Minute-level close price",
                    "dependencies": {},
                    "parameters": {"independent_factor_related_entity_key":"underlying_asset_id"}
                },
                        "implied_volatility": {
                    "class": CompanyShareFactor, 
                    "name": "close",#needs to be close open volume or
                    "group": "implied_volatility",
                    "subgroup": "minutes",
                    "frequency": "1m",
                    "data_type": "numeric",
                    "description": "Minute-level open volatility",
                    "dependencies": [],
                    "parameters": {"independent_factor_related_entity_key":"underlying_asset_id"}
                },
                #         "yield": {
                #     "class": CompanyShareFactor, 
                #     "name": "implied_volatility",
                #     "group": "implied_volatility",
                #     "subgroup": "minutes",
                #     "frequency": "1m",
                #     "data_type": "numeric",
                #     "description": "Minute-level open volatility",
                #     "dependencies": [],
                #     "parameters": {"independent_factor_entity_id":"currency_id"}
                # },
        },
        "parameters": {}
    },
    "option_mid_price": {
        "class": CompanyShareOptionMidPriceFactor,
        "name": "option_mid_price",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level mid price return",
        "dependencies": {
                        "mid": {
                    "class": CompanyShareFactor,
                    "name": "mid",
                    "group": "price",
                    "subgroup": "minutes",
                    "frequency": "1m",
                    "data_type": "numeric",
                    "dependencies": {},
                    "parameters": {"independent_factor_related_entity_key":"underlying_asset_id"}
                },
                  
        },
        "parameters": {}
    },

    "return_open": {
        "class": CompanyShareOptionPriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": CompanyShareOptionFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": CompanyShareOptionFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=4, hours=3, minutes=10)}
                },
                },
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
        "dependencies": {
            "start_price": {
                "class": CompanyShareOptionFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanyShareOptionFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=1, hours=0, minutes=0)}
            }
        },
        "parameters": {"period": "1D"}
    },
    
    # Advanced Pricing Model Factors
    "black_scholes_merton_price": {
        "class": CompanyShareOptionBlackScholesMertonPriceFactor,
        "name": "black_scholes_merton_price",
        "group": "price_model",
        "subgroup": "black_scholes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Black-Scholes-Merton option price with dividend yield",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            },
            "implied_volatility": {
                "class": CompanyShareFactor,
                "name": "implied_volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Implied volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {}
    },

    "cox_ross_rubinstein_price": {
        "class": CompanyShareOptionCoxRossRubinsteinPriceFactor,
        "name": "cox_ross_rubinstein_price",
        "group": "price_model",
        "subgroup": "binomial_tree",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Cox-Ross-Rubinstein binomial tree option price",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {"tree_steps": 100}
    },

    "heston_price": {
        "class": CompanyShareOptionHestonPriceFactor,
        "name": "heston_price",
        "group": "price_model",
        "subgroup": "stochastic_volatility",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Heston stochastic volatility option price",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            },
            "volatility": {
                "class": CompanyShareFactor,
                "name": "volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Current volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {"monte_carlo_paths": 10000}
    },

    "hull_white_price": {
        "class": CompanyShareOptionHullWhitePriceFactor,
        "name": "hull_white_price",
        "group": "price_model",
        "subgroup": "stochastic_rates",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Hull-White stochastic interest rate option price",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {}
    },

    "sabr_price": {
        "class": CompanyShareOptionSABRPriceFactor,
        "name": "sabr_price",
        "group": "price_model",
        "subgroup": "sabr",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "SABR model option price with volatility smile",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {}
    },

    "bates_price": {
        "class": CompanyShareOptionBatesPriceFactor,
        "name": "bates_price",
        "group": "price_model",
        "subgroup": "jump_diffusion",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Bates jump-diffusion option price",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            },
            "volatility": {
                "class": CompanyShareFactor,
                "name": "volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Current volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {"monte_carlo_paths": 10000}
    },

    "dupire_local_volatility_price": {
        "class": CompanyShareOptionDupireLocalVolatilityPriceFactor,
        "name": "dupire_local_volatility_price",
        "group": "price_model",
        "subgroup": "local_volatility",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Dupire local volatility option price",
        "dependencies": {
            "underlying_price": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Underlying asset price",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_asset_id"}
            }
        },
        "parameters": {"grid_size": 100}
    },
    
}