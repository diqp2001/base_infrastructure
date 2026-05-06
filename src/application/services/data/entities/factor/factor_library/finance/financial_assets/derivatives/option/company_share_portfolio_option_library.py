from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_factor import CompanySharePortfolioOptionPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_return_factor import CompanySharePortfolioOptionPriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor

# Portfolio Pricing model factors
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_black_scholes_merton_price_factor import CompanySharePortfolioOptionBlackScholesMertonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_cox_ross_rubinstein_price_factor import CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_heston_price_factor import CompanySharePortfolioOptionHestonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_hull_white_price_factor import CompanySharePortfolioOptionHullWhitePriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_sabr_price_factor import CompanySharePortfolioOptionSABRPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_bates_price_factor import CompanySharePortfolioOptionBatesPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_dupire_local_volatility_price_factor import CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor


COMPANY_SHARE_PORTFOLIO_OPTION_LIBRARY: Dict[str, Dict] = {
    
    "open": {
        "class": CompanySharePortfolioOptionFactor, 
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
        "class": CompanySharePortfolioOptionFactor, 
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
        "class": CompanySharePortfolioOptionFactor, 
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
        "class": CompanySharePortfolioOptionFactor, 
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
        "class": CompanySharePortfolioOptionFactor, 
        "name": "volume",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level traded volume",
        "dependencies": [],
        "parameters": {}
    },
    
    "portfolio_option_price": {
        "class": CompanySharePortfolioOptionPriceFactor,
        "name": "portfolio_option_price",
        "group": "price",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio option price with underlying dependencies",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": {},
                "parameters": {"independent_factor_related_entity_key":"underlying_portfolio_id"}
            },
            "implied_volatility": {
                "class": CompanyShareFactor, 
                "name": "implied_volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio implied volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key":"underlying_portfolio_id"}
            }
        },
        "parameters": {}
    },

    "return_open": {
        "class": CompanySharePortfolioOptionPriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": CompanySharePortfolioOptionFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": CompanySharePortfolioOptionFactor,
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
        "class": CompanySharePortfolioOptionPriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": CompanySharePortfolioOptionFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": CompanySharePortfolioOptionFactor,
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
    
    # Advanced Portfolio Pricing Model Factors
    "portfolio_black_scholes_merton_price": {
        "class": CompanySharePortfolioOptionBlackScholesMertonPriceFactor,
        "name": "portfolio_black_scholes_merton_price",
        "group": "price_model",
        "subgroup": "portfolio_black_scholes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio Black-Scholes-Merton option price with multi-asset correlation",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            },
            "portfolio_volatility": {
                "class": CompanyShareFactor,
                "name": "portfolio_volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {}
    },

    "portfolio_cox_ross_rubinstein_price": {
        "class": CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor,
        "name": "portfolio_cox_ross_rubinstein_price",
        "group": "price_model",
        "subgroup": "portfolio_binomial_tree",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio Cox-Ross-Rubinstein binomial tree option price",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {"tree_steps": 50, "max_assets": 5}
    },

    "portfolio_heston_price": {
        "class": CompanySharePortfolioOptionHestonPriceFactor,
        "name": "portfolio_heston_price",
        "group": "price_model",
        "subgroup": "portfolio_stochastic_volatility",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio Heston stochastic volatility option price",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            },
            "portfolio_volatility": {
                "class": CompanyShareFactor,
                "name": "portfolio_volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {"monte_carlo_paths": 5000}
    },

    "portfolio_hull_white_price": {
        "class": CompanySharePortfolioOptionHullWhitePriceFactor,
        "name": "portfolio_hull_white_price",
        "group": "price_model",
        "subgroup": "portfolio_stochastic_rates",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio Hull-White stochastic interest rate option price",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {}
    },

    "portfolio_sabr_price": {
        "class": CompanySharePortfolioOptionSABRPriceFactor,
        "name": "portfolio_sabr_price",
        "group": "price_model",
        "subgroup": "portfolio_sabr",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio SABR model option price with multi-asset volatility smile",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {}
    },

    "portfolio_bates_price": {
        "class": CompanySharePortfolioOptionBatesPriceFactor,
        "name": "portfolio_bates_price",
        "group": "price_model",
        "subgroup": "portfolio_jump_diffusion",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio Bates jump-diffusion option price",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            },
            "portfolio_volatility": {
                "class": CompanyShareFactor,
                "name": "portfolio_volatility",
                "group": "volatility",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio volatility",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {"monte_carlo_paths": 5000}
    },

    "portfolio_dupire_local_volatility_price": {
        "class": CompanySharePortfolioOptionDupireLocalVolatilityPriceFactor,
        "name": "portfolio_dupire_local_volatility_price",
        "group": "price_model",
        "subgroup": "portfolio_local_volatility",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Portfolio Dupire local volatility option price",
        "dependencies": {
            "portfolio_value": {
                "class": CompanyShareFactor,
                "name": "close",
                "group": "price",
                "subgroup": "minutes",
                "frequency": "1m",
                "data_type": "numeric",
                "description": "Portfolio underlying value",
                "dependencies": [],
                "parameters": {"independent_factor_related_entity_key": "underlying_portfolio_id"}
            }
        },
        "parameters": {"grid_size": 50}
    },
    
}