# domain/entities/factor/finance/financial_assets/share_factor/momentum_factor_share.py

from __future__ import annotations


class ShareMomentumFactor(ShareFactor):
    """
    Domain entity representing a momentum factor for shares.
    Contains only business logic. No ORM dependencies.
    """

    def calculate(self, prices, period: int, **kwargs):
        """
        Example domain logic: compute momentum based on past prices.
        Replace with actual logic.
        """
        if len(prices) < period:
            return None

        return (prices[-1] / prices[-period]) - 1
