# domain/entities/factor/finance/financial_assets/share_factor/volatility_factor_share.py

from __future__ import annotations

# Import from unified factor model for backward compatibility
from src.infrastructure.models.factor.factor_model import ShareVolatilityFactor as UnifiedShareVolatilityFactor

# Export the unified model as ShareVolatilityFactor for backward compatibility
ShareVolatilityFactor = UnifiedShareVolatilityFactor