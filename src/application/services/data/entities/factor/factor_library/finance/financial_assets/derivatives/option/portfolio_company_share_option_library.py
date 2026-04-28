
from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_factor import PortfolioCompanyShareOptionPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_return_factor import PortfolioCompanyShareOptionPriceReturnFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor

# Portfolio Pricing model factors
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_black_scholes_merton_price_factor import PortfolioCompanyShareOptionBlackScholesMertonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_cox_ross_rubinstein_price_factor import PortfolioCompanyShareOptionCoxRossRubinsteinPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_heston_price_factor import PortfolioCompanyShareOptionHestonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_hull_white_price_factor import PortfolioCompanyShareOptionHullWhitePriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_sabr_price_factor import PortfolioCompanyShareOptionSABRPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_bates_price_factor import PortfolioCompanyShareOptionBatesPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_dupire_local_volatility_price_factor import PortfolioCompanyShareOptionDupireLocalVolatilityPriceFactor


PORTFOLIO_COMPANY_SHARE_OPTION_LIBRARY: Dict[str, Dict] = {
    
    "open": {
        "class": PortfolioCompanyShareOptionFactor, 
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
        "class": PortfolioCompanyShareOptionFactor, 
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
        "class": PortfolioCompanyShareOptionFactor, 
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
        "class": PortfolioCompanyShareOptionFactor, 
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
        "class": PortfolioCompanyShareOptionFactor, 
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
        "class": PortfolioCompanyShareOptionPriceFactor,
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
        "class": PortfolioCompanyShareOptionPriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": PortfolioCompanyShareOptionFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": PortfolioCompanyShareOptionFactor,
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
        "class": PortfolioCompanyShareOptionPriceReturnFactor,
        "name": "return_daily",
        "group": "return",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "description": "Daily price return",
        "dependencies": {
            "start_price": {
                "class": PortfolioCompanyShareOptionFactor,
                "name": "close",
                "group": "price",
                "subgroup": "daily",
                "data_type": "numeric",
                "description": "Daily close price",
                "dependencies": [],
                "parameters": {"lag": timedelta(days=2, hours=0, minutes=0)}
            },
            "end_price": {
                "class": PortfolioCompanyShareOptionFactor,
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
        "class": PortfolioCompanyShareOptionBlackScholesMertonPriceFactor,
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
        "class": PortfolioCompanyShareOptionCoxRossRubinsteinPriceFactor,
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
        "class": PortfolioCompanyShareOptionHestonPriceFactor,
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
        "class": PortfolioCompanyShareOptionHullWhitePriceFactor,
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
        "class": PortfolioCompanyShareOptionSABRPriceFactor,
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
        "class": PortfolioCompanyShareOptionBatesPriceFactor,
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
        "class": PortfolioCompanyShareOptionDupireLocalVolatilityPriceFactor,
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