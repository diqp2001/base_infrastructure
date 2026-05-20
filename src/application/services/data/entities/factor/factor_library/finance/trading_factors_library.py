"""
Trading factors library - Position, Transaction, and Order factors.

This library defines the factor dependencies for the trading lifecycle:
Order → Transaction → Position → Holding → Portfolio
"""

from datetime import timedelta
from typing import Dict

from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor


TRADING_FACTORS_LIBRARY: Dict[str, Dict] = {
    
    # Base Order Factors (no dependencies)
    "order_quantity": {
        "class": CompanyShareOrderQuantityFactor,
        "name": "order_quantity",
        "group": "order",
        "subgroup": "quantity",
        "frequency": "1d",
        "data_type": "numeric",
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
        "data_type": "decimal",
        "description": "Price per share in company share order",
        "dependencies": {},
        "parameters": {}
    },
    
    # Transaction Value Factor (depends on order quantity and price)
    "transaction_value": {
        "class": CompanyShareTransactionValueFactor,
        "name": "transaction_value",
        "group": "transaction",
        "subgroup": "value",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "Total value of company share transaction (quantity × price)",
        "dependencies": {
            "order_quantity": {
                "class": CompanyShareOrderQuantityFactor,
                "name": "order_quantity",
                "group": "order",
                "subgroup": "quantity",
                "data_type": "numeric",
                "description": "Order quantity dependency",
                "dependencies": {},
                "parameters": {"lag": None, "independent_factor_related_entity_key": "order_id"}
            },
            "order_price": {
                "class": CompanyShareOrderPriceFactor,
                "name": "order_price",
                "group": "order",
                "subgroup": "price",
                "data_type": "decimal",
                "description": "Order price dependency",
                "dependencies": {},
                "parameters": {"lag": None, "independent_factor_related_entity_key": "order_id"}
            }
        },
        "parameters": {}
    },
    
    # Position Value Factor (depends on transaction values)
    "position_value": {
        "class": CompanySharePositionValueFactor,
        "name": "position_value",
        "group": "position",
        "subgroup": "value",
        "frequency": "1d",
        "data_type": "decimal",
        "description": "Total value of company share position from transactions",
        "dependencies": {
            "transaction_values": {
                "class": CompanyShareTransactionValueFactor,
                "name": "transaction_value",
                "group": "transaction",
                "subgroup": "value",
                "data_type": "decimal",
                "description": "Transaction value dependency",
                "dependencies": {},
                "parameters": {"lag": None, "independent_factor_related_entity_key": "transaction_id"}
            }
        },
        "parameters": {}
    }
}