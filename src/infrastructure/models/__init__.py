

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
from src.infrastructure.models.finance.financial_assets.derivatives import Derivative, UnderlyingAsset
from src.infrastructure.models.finance.financial_assets.forward_contract import (
    ForwardContract, CommodityForward, CurrencyForward
)
from infrastructure.models.finance.financial_assets.swap.swap import Swap
from infrastructure.models.finance.financial_assets.swap.currency_swap import CurrencySwap
from infrastructure.models.finance.financial_assets.swap.interest_rate_swap import InterestRateSwap
from infrastructure.models.finance.financial_assets.swap.swap_leg import SwapLeg


# New general entity imports
from src.infrastructure.models.continent import Continent

# New finance entity imports
from src.infrastructure.models.finance.portfolio import Portfolio
from src.infrastructure.models.finance.position import Position
from src.infrastructure.models.finance.security_holdings import SecurityHoldingsModel
from src.infrastructure.models.finance.portfolio_holdings import PortfolioHoldingsModel
from src.infrastructure.models.finance.portfolio_statistics import PortfolioStatisticsModel
from src.infrastructure.models.finance.market_data import MarketDataModel

# Holding models
from src.infrastructure.models.finance.holding import (
    HoldingModel, 
    PortfolioHoldingModel, 
    PortfolioCompanyShareHoldingModel
)

# Portfolio company share option model
from src.infrastructure.models.finance.financial_assets.portfolio_company_share_option import PortfolioCompanyShareOptionModel
