"""
Model components of the base project template.

Only the model trainer exists in the template; projects add their own models
(see market_making_SPX_call_spread_project/models for pricing / volatility models).
"""

from .model_trainer import ModelTrainer

__all__ = ['ModelTrainer']
