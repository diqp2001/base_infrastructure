from datetime import timedelta
from typing import Dict, List

from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor
from src.domain.entities.factor.finance.holding.portfolio_holding_value_factor import PortfolioHoldingValueFactor
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor
from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor
from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor


PORTFOLIO_LIBRARY: Dict[str, Dict] = {
    "portfolio_value": {
        "class": PortfolioValueFactor,
        "entity_class": PortfolioValueFactor,
        "name": "portfolio_value",
        "entity_symbol": "portfolio_value",
        "group": "value",
        "subgroup": "daily",
        "frequency": "1d",
        "data_type": "numeric",
        "factor_type": "portfolio_value_factor",
        "source": "calculated",
        "definition": "Portfolio value calculated from sum of holding values",
        "description": "Daily value of the portfolio calculated from holding values",
        "dependencies": {
            "holding_value": {
                "class": PortfolioHoldingValueFactor,
                "name": "holding_value",
                "group": "holding",
                "subgroup": "value",
                "frequency": "1d",
                "data_type": "numeric",
                "factor_type": "portfolio_holding_value_factor",
                "source": "calculated",
                "definition": "Holding value calculated from sum of position values",
                "description": "Daily value of each holding in the portfolio",
                "dependencies": {
                    "company_share_portfolio_value": {
                        "class": CompanySharePortfolioValueFactor,
                        "name": "company_share_portfolio_value",
                        "group": "value",
                        "subgroup": "daily",
                        "frequency": "1d",
                        "data_type": "numeric",
                        "factor_type": "company_share_portfolio_value_factor",
                        "source": "calculated",
                        "definition": "Company share portfolio value from holding values",
                        "description": "Daily value of company share portfolio calculated from holding values",
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
                                "description": "Daily value of each company share holding in the portfolio",
                                "dependencies": {
                                    "position_value": {
                                        "class": CompanySharePositionValueFactor,
                                        "name": "position_value",
                                        "group": "position",
                                        "subgroup": "value",
                                        "frequency": "1d",
                                        "data_type": "numeric",
                                        "factor_type": "company_share_position_value_factor",
                                        "source": "calculated",
                                        "definition": "Position value from sum of transaction values",
                                        "description": "Total value of company share position from transactions",
                                        "dependencies": {
                                            "transaction_value": {
                                                "class": CompanyShareTransactionValueFactor,
                                                "name": "transaction_value",
                                                "group": "transaction",
                                                "subgroup": "value",
                                                "frequency": "1d",
                                                "data_type": "numeric",
                                                "factor_type": "company_share_transaction_value_factor",
                                                "source": "calculated",
                                                "definition": "Transaction value calculated from quantity × price",
                                                "description": "Total value of company share transaction (quantity × price)",
                                                "dependencies": {
                                                    "order_quantity": {
                                                        "class": CompanyShareOrderQuantityFactor,
                                                        "name": "order_quantity",
                                                        "group": "order",
                                                        "subgroup": "quantity",
                                                        "frequency": "1d",
                                                        "data_type": "numeric",
                                                        "factor_type": "company_share_order_quantity_factor",
                                                        "source": "order_data",
                                                        "definition": "Order quantity from order execution",
                                                        "description": "Number of shares in company share order",
                                                        "dependencies": {},
                                                        "parameters": {}
                                                    },
                                                    "order_price": {
                                                        "class": CompanyShareOrderPriceFactor,
                                                        "name": "order_price",
                                                        "group": "order",
                                                        "subgroup": "price",
                                                        "frequency": "1d",
                                                        "data_type": "numeric",
                                                        "factor_type": "company_share_order_price_factor",
                                                        "source": "order_data",
                                                        "definition": "Order price from order execution",
                                                        "description": "Price per share in company share order",
                                                        "dependencies": {},
                                                        "parameters": {}
                                                    }
                                                },
                                                "parameters": {}
                                            }
                                        },
                                        "parameters": {}
                                    }
                                },
                                "parameters": {"period": "1D"}
                            }
                        },
                        "parameters": {"period": "1D"}
                    }
                },
                "parameters": {}
            }
        },
        "parameters": {"period": "1D"}
    }
}