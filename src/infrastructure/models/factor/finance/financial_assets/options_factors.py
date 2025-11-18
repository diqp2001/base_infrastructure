"""
SQLAlchemy ORM models for Options factor entities.
DEPRECATED: Use unified factor model from factor_model.py instead.
This file exists for backward compatibility and imports from the unified model.
"""

# Import from the unified factor model
from src.infrastructure.models.factor.factor_model import (
    OptionsFactor,
    FactorValue as OptionsFactorValue  # Alias for backward compatibility
)