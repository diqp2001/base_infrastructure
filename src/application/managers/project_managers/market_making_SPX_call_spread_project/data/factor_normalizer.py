"""
Re-export the shared FactorNormalizer from misbuffet.

All normalization logic lives in:
  src/application/services/misbuffet/data/factor_normalizer.py
"""

from src.application.services.misbuffet.data.factor_normalizer import (  # noqa: F401
    FactorNormalizer,
    NormalizationMethod,
    NormalizationScope,
    NormalizationConfig,
)
