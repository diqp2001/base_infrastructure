from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.holding.company_share_portfolio_portfolio.company_share_portfolio_portfolio_holding_value_factor import CompanySharePortfolioPortfolioHoldingValueFactor
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor
from src.domain.entities.factor.finance.holding.portfolio_holding_value_factor import PortfolioHoldingValueFactor
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor
from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor
from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor
from src.domain.entities.factor.finance.holding.company_share_option_portfolio_portfolio.company_share_option_portfolio_portfolio_holding_value_factor import CompanyShareOptionPortfolioPortfolioHoldingValueFactor
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_value_factor import CompanyShareOptionPortfolioValueFactor
from src.domain.entities.factor.finance.holding.company_share_option_portfolio.company_share_option_portfolio_holding_value_factor import CompanyShareOptionPortfolioHoldingValueFactor


PORTFOLIO_LIBRARY: Dict[str, Dict] = {
    "portfolio_value": {
        "class": PortfolioValueFactor,
        "entity_class": PortfolioValueFactor,
        "name": "portfolio_value",
        "entity_symbol": "portfolio_value",
        "group": "value",
        "subgroup": "minutes",
        "frequency": "1d",
        "data_type": "numeric",
        "factor_type": "portfolio_value_factor",
        "source": "calculated",
        "definition": "Portfolio value calculated from sum of holding values",
        "description": "1-day value of the portfolio calculated from holding values",
        "dependencies": {
            "holding_value": {
                "class": CompanySharePortfolioPortfolioHoldingValueFactor,
                "name": "holding_value",
                "group": "holding",
                "subgroup": "value",
                "frequency": "1d",
                "data_type": "numeric",
                "factor_type": "company_share_portfolio_portfolio_holding_value_factor",
                "source": "calculated",
                "definition": "Holding value calculated from sum of position values",
                "description": "1-day value of each holding in the portfolio",
                "dependencies": {
                    "company_share_portfolio_value": {
                        "class": CompanySharePortfolioValueFactor,
                        "name": "company_share_portfolio_value",
                        "group": "value",
                        "subgroup": "minutes",
                        "frequency": "5m",
                        "data_type": "numeric",
                        "factor_type": "company_share_portfolio_value_factor",
                        "source": "calculated",
                        "definition": "Company share portfolio value from holding values",
                        "description": "5-minute value of company share portfolio calculated from holding values",
                        "dependencies": {
                            "company_share_portfolio_holding_value": {
                                "class": CompanySharePortfolioHoldingValueFactor,
                                "name": "company_share_portfolio_holding_value",
                                "group": "holding",
                                "subgroup": "value",
                                "frequency": "1d",
                                "data_type": "numeric",
                                "factor_type": "company_share_portfolio_holding_value_factor",
                                "source": "calculated",
                                "definition": "Company share holding value from position values",
                                "description": "1-day value of each company share holding in the portfolio",
                                "dependencies": {},
                                "parameters": {"period": "1d"}
                            }
                        },
                        "parameters": {"period": "1d"}
                    }
                },
                "parameters": {}
            },
            "cso_holding_value": {
                "class": CompanyShareOptionPortfolioPortfolioHoldingValueFactor,
                "name": "cso_holding_value",
                "group": "holding",
                "subgroup": "value",
                "frequency": "1d",
                "data_type": "numeric",
                "factor_type": "company_share_option_portfolio_portfolio_holding_value_factor",
                "source": "calculated",
                "definition": "Holding value of company share option sub-portfolio",
                "description": "1-day value of the CSO sub-portfolio holding",
                "dependencies": {
                    "company_share_option_portfolio_value": {
                        "class": CompanyShareOptionPortfolioValueFactor,
                        "name": "company_share_option_portfolio_value",
                        "group": "value",
                        "subgroup": "value",
                        "frequency": "1d",
                        "data_type": "numeric",
                        "factor_type": "company_share_option_portfolio_value_factor",
                        "source": "calculated",
                        "definition": "Company share option portfolio value from holding values",
                        "description": "1-day value of company share option portfolio",
                        "dependencies": {
                            "company_share_option_portfolio_holding_value": {
                                "class": CompanyShareOptionPortfolioHoldingValueFactor,
                                "name": "company_share_option_portfolio_holding_value",
                                "group": "holding",
                                "subgroup": "value",
                                "frequency": "1d",
                                "data_type": "numeric",
                                "factor_type": "company_share_option_portfolio_holding_value_factor",
                                "source": "calculated",
                                "definition": "Company share option holding value from position values",
                                "description": "1-day value of each company share option holding",
                                "dependencies": {},
                                "parameters": {"period": "1d"}
                            }
                        },
                        "parameters": {"period": "1d"}
                    }
                },
                "parameters": {}
            }
        },
        "parameters": {"period": "1d"}
    }
}