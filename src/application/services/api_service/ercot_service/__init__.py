"""
ERCOT Service Package

Provides access to ERCOT (Electric Reliability Council of Texas) APIs
for energy market data including day-ahead and real-time market prices.

Two service implementations:
- ErcotPublicApiService: Public API access (no auth, 90-day limit)
- ErcotAuthenticatedApiService: Enhanced access with credentials
"""

from .ercot_public_api_service import ErcotPublicApiService
from .ercot_authenticated_api_service import (
    ErcotAuthenticatedApiService,
    ERCOTCredentials,
    ERCOTRateLimit
)

__all__ = [
    'ErcotPublicApiService',
    'ErcotAuthenticatedApiService',
    'ERCOTCredentials',
    'ERCOTRateLimit'
]