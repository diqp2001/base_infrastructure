"""
IBKR Financial Assets Repositories - Interactive Brokers financial asset repositories.

This module contains IBKR repository implementations following the dual inheritance pattern:
- Each repository inherits from appropriate base repository class (ShareRepository, FinancialAssetBaseRepository)  
- Each repository implements the corresponding port interface
- IBKR repositories delegate persistence to local repositories
- IBKR-specific business rules and data transformation are applied
"""

from .company_share_repository import IBKRCompanyShareRepository
from .bond_repository import IBKRBondRepository
from .currency_repository import IBKRCurrencyRepository
from .etf_share_repository import IBKRETFShareRepository
from .cash_repository import IBKRCashRepository
from .commodity_repository import IBKRCommodityRepository
from .crypto_repository import IBKRCryptoRepository
from .equity_repository import IBKREquityRepository
from .index_repository import IBKRIndexRepository
from .derivatives.future.index_future_repository import IBKRIndexFutureRepository
from .security_repository import IBKRSecurityRepository
from .share_repository import IBKRShareRepository

__all__ = [
    'IBKRCompanyShareRepository',
    'IBKRBondRepository', 
    'IBKRCurrencyRepository',
    'IBKRETFShareRepository',
    'IBKRCashRepository',
    'IBKRCommodityRepository',
    'IBKRCryptoRepository',
    'IBKREquityRepository',
    'IBKRIndexRepository',
    'IBKRIndexFutureRepository',
    'IBKRSecurityRepository',
    'IBKRShareRepository'
]