"""
Strategy components of the base project template.

Only the strategy exists in the template; projects add their own risk manager
(see market_making_SPX_call_spread_project/strategy/risk_manager.py).
"""

from .market_making_strategy import Strategy

__all__ = ['Strategy']
