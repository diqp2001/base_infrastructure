#src/infrastructure/models/__init__.py
"""
SQLAlchemy Model Registry for Base Infrastructure

This module provides the DeclarativeBase and imports all models to ensure they are
registered with SQLAlchemy's class registry for string relationship resolution.

IMPORTANT: All models MUST be imported here to be available for relationships.
"""

from sqlalchemy.orm import DeclarativeBase

class ModelBase(DeclarativeBase):
    """Base class for all ORM models"""
    pass

# =============================================================================
# MODEL REGISTRATION - Required for SQLAlchemy string relationship resolution
# =============================================================================

# Core geographical and organizational models (no dependencies)
from src.infrastructure.models.country import Country
from src.infrastructure.models.industry import Industry
from src.infrastructure.models.sector import Sector

# Financial infrastructure (depends on geographical models)
from src.infrastructure.models.finance.exchange import Exchange
from src.infrastructure.models.finance.company import Company

# Basic financial assets (depends on exchange/company)
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAsset
from src.infrastructure.models.finance.financial_assets.currency import Currency
from src.infrastructure.models.finance.financial_assets.cash import Cash
from src.infrastructure.models.finance.financial_assets.commodity import Commodity
from src.infrastructure.models.finance.financial_assets.security import Security
from src.infrastructure.models.finance.financial_assets.equity import Equity

# Share-based assets (depends on exchange/company)
from src.infrastructure.models.finance.financial_assets.share import Share
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShare

# Complex financial instruments
from src.infrastructure.models.finance.financial_assets.bond import Bond
from src.infrastructure.models.finance.financial_assets.options import Options
from src.infrastructure.models.finance.financial_assets.derivatives import Derivative, UnderlyingAsset
from src.infrastructure.models.finance.financial_assets.forward_contract import (
    ForwardContract, CommodityForward, CurrencyForward
)

# Swap instruments
from src.infrastructure.models.finance.financial_assets.swap.swap import Swap
from src.infrastructure.models.finance.financial_assets.swap.currency_swap import CurrencySwap
from src.infrastructure.models.finance.financial_assets.swap.interest_rate_swap import InterestRateSwap
from src.infrastructure.models.finance.financial_assets.swap.swap_leg import SwapLeg

# Portfolio and holdings (depends on all asset types)
from src.infrastructure.models.finance.portfolio.portfolio import Portfolio
from src.infrastructure.models.finance.portfolio.portfolio_derivative import PortfolioDerivative
from src.infrastructure.models.finance.portfolio.portfolio_company_share import PortfolioCompanyShare
from src.infrastructure.models.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOption
from src.infrastructure.models.finance.security_holding import SecurityHolding
from src.infrastructure.models.finance.market_data import MarketData
from src.infrastructure.models.finance.instrument import Instrument

# Holding models
from src.infrastructure.models.finance.holding.holding import Holding
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldings
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding

# Portfolio options


# Geographic models
from src.infrastructure.models.continent import Continent

# =============================================================================
# INTEGRATION WITH EXISTING REGISTRY SYSTEM
# =============================================================================

def ensure_models_registered():
    """
    Verifies that all models are properly registered with SQLAlchemy.
    This function integrates with your existing BaseFactory and ModelRegistry system.
    """
    from src.infrastructure.models import ModelBase
    registered = list(ModelBase.registry._class_registry.keys())
    
    # Core models that must be registered for string relationships to work
    required_models = {
        'Country', 'Industry', 'Sector', 'Exchange', 'Company', 
        'Share', 'CompanyShare', 'ETFShare', 'Portfolio','PortfolioDerivative','PortfolioCompanyShare','PortfolioCompanyShareOption', 'Holding'
    }
    
    missing = required_models - set(registered)
    if missing:
        raise RuntimeError(f"Critical models not registered: {missing}")
    
    return registered

# Register models immediately on import
try:
    ensure_models_registered()
    print(f"✅ SQLAlchemy models successfully registered: {len(ModelBase.registry._class_registry)} models")
except RuntimeError as e:
    print(f"❌ SQLAlchemy model registration error: {e}")
    raise

# =============================================================================
# PUBLIC API - Compatible with existing BaseFactory system
# =============================================================================

__all__ = [
    'ModelBase',
    'Country', 'Industry', 'Sector', 'Continent',
    'Exchange', 'Company',
    'FinancialAsset', 'Currency', 'Cash', 'Commodity', 'Security', 'Equity',
    'Share', 'CompanyShare', 'ETFShare',
    'Bond', 'Options', 'Derivative', 'UnderlyingAsset',
    'ForwardContract', 'CommodityForward', 'CurrencyForward',
    'Swap', 'CurrencySwap', 'InterestRateSwap', 'SwapLeg',
    'Portfolio','PortfolioDerivative','PortfolioCompanyShare','PortfolioCompanyShareOption', 'SecurityHolding', 'MarketData', 'Instrument',
    'Holding', 'PortfolioHoldings', 'PortfolioCompanyShareHolding',
    'ensure_models_registered'
]