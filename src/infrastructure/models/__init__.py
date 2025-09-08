

from sqlalchemy.orm import DeclarativeBase

class ModelBase(DeclarativeBase):
    pass

# Existing imports
from src.infrastructure.models.finance.financial_assets.share import Share
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShare
from src.infrastructure.models.finance.financial_assets.crypto import Crypto
from src.infrastructure.models.finance.financial_assets.bond import Bond
from src.infrastructure.models.finance.financial_assets.index import Index
from src.infrastructure.models.finance.financial_assets.options import Options
from src.infrastructure.models.finance.financial_assets.futures import Futures
from src.infrastructure.models.finance.exchange import Exchange
from src.infrastructure.models.finance.company import Company
from src.infrastructure.models.country import Country
from src.infrastructure.models.industry import Industry
from src.infrastructure.models.sector import Sector

# New financial asset imports
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAsset
from src.infrastructure.models.finance.financial_assets.currency import Currency
from src.infrastructure.models.finance.financial_assets.cash import Cash
from src.infrastructure.models.finance.financial_assets.commodity import Commodity
from src.infrastructure.models.finance.financial_assets.security import Security
from src.infrastructure.models.finance.financial_assets.equity import Equity
from src.infrastructure.models.finance.financial_assets.stock import Stock
from src.infrastructure.models.finance.financial_assets.derivatives import Derivative, UnderlyingAsset
from src.infrastructure.models.finance.financial_assets.forward_contract import (
    ForwardContract, CommodityForward, CurrencyForward
)
from src.infrastructure.models.finance.financial_assets.swaps import (
    Swap, SwapLeg, InterestRateSwap, CurrencySwap
)

# New general entity imports
from src.infrastructure.models.continent import Continent

# New finance entity imports
from src.infrastructure.models.finance.portfolio import Portfolio
from src.infrastructure.models.finance.position import Position
