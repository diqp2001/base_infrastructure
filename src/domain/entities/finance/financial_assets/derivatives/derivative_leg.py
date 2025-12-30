from __future__ import annotations
from typing import Optional
from decimal import Decimal

from domain.entities.finance.financial_assets.derivatives.derivative import Derivative


class DerivativeLeg:
    """
    One leg inside a structured derivative (option, future, etc.).
    """

    def __init__(
        self,
        derivative: Derivative,
        quantity: Decimal,
    ):
        self.derivative = derivative
        self.quantity = quantity
