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
# Geographic models
from src.infrastructure.models.continent import ContinentModel
from src.infrastructure.models.country import CountryModel
from src.infrastructure.models.industry import IndustryModel
from src.infrastructure.models.sector import SectorModel

# Financial infrastructure (depends on geographical models)
from src.infrastructure.models.finance.exchange import ExchangeModel
from src.infrastructure.models.finance.company import CompanyModel

# Financial statements (depends on company)
from src.infrastructure.models.finance.financial_statements.financial_statement import FinancialStatementModel
from src.infrastructure.models.finance.financial_statements.balance_sheet import BalanceSheetModel
from src.infrastructure.models.finance.financial_statements.income_statement import IncomeStatementModel
from src.infrastructure.models.finance.financial_statements.cash_flow_statement import CashFlowStatementModel


# Basic financial assets (depends on exchange/company)
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel
from src.infrastructure.models.finance.financial_assets.cash import CashModel
from src.infrastructure.models.finance.financial_assets.commodity import CommodityModel
from src.infrastructure.models.finance.financial_assets.security import SecurityModel
from src.infrastructure.models.finance.financial_assets.equity import EquityModel

# Share-based assets (depends on exchange/company)
from src.infrastructure.models.finance.financial_assets.share import ShareModel
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel

# Complex financial instruments
from src.infrastructure.models.finance.financial_assets.bond import BondModel
from src.infrastructure.models.finance.financial_assets.derivative.option.options import OptionsModel
from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import CompanyShareOptionModel
from src.infrastructure.models.finance.financial_assets.derivative.option.index_future_option import IndexFutureOptionModel
from src.infrastructure.models.finance.financial_assets.derivative.future.future import FutureModel
from src.infrastructure.models.finance.financial_assets.derivative.future.index_future import IndexFutureModel
from src.infrastructure.models.finance.financial_assets.derivative.derivatives import DerivativeModel
from src.infrastructure.models.finance.financial_assets.derivative.forward_contract import (
    ForwardContractModel
)
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel
# Swap instruments
from src.infrastructure.models.finance.financial_assets.derivative.swap.swap import SwapModel
from src.infrastructure.models.finance.financial_assets.derivative.swap.swap_leg import SwapLegModel

# Portfolio and holdings (depends on all asset types)
from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
from src.infrastructure.models.finance.portfolio.portfolio_derivative import PortfolioDerivativeModel
from src.infrastructure.models.finance.portfolio.portfolio_company_share import PortfolioCompanyShareModel
from src.infrastructure.models.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOptionModel
from src.infrastructure.models.finance.position import PositionModel
from src.infrastructure.models.finance.market_data import MarketDataModel
from src.infrastructure.models.finance.instrument import InstrumentModel

# Holding models
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldingsModel
from src.infrastructure.models.finance.holding.security_holding import SecurityHoldingModel
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHoldingModel

# Account, Order, and Transaction models
from src.infrastructure.models.finance.account import AccountModel
from src.infrastructure.models.finance.order.order import OrderModel
from src.infrastructure.models.finance.transaction.transaction import TransactionModel

# Portfolio options




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
        'CountryModel', 'IndustryModel', 'SectorModel', 'ExchangeModel', 'CompanyModel',
        'FinancialStatementModel', 'BalanceSheetModel', 'IncomeStatementModel', 'CashFlowStatementModel',
        'ShareModel', 'CompanyShareModel', 'ETFShareModel', 'PortfolioModel','PortfolioDerivativeModel',
        'PortfolioCompanyShareModel','PortfolioCompanyShareOptionModel', 'HoldingModel',
        'IndexFutureOptionModel', 'IndexFutureModel', 'OptionsModel', 'CompanyShareOptionModel',
        'AccountModel', 'OrderModel', 'TransactionModel'
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
    'CountryModel', 'IndustryModel', 'SectorModel', 'ContinentModel',
    'ExchangeModel', 'CompanyModel',
    'FinancialStatementModel', 'BalanceSheetModel', 'IncomeStatementModel', 'CashFlowStatementModel',
    'FinancialAssetModel', 'CurrencyModel', 'CashModel', 'CommodityModel', 'SecurityModel', 'EquityModel',
    'ShareModel', 'CompanyShareModel', 'ETFShareModel',
    'BondModel', 'OptionsModel', 'CompanyShareOptionModel', 'IndexFutureOptionModel', 'FutureModel', 'IndexFutureModel','DerivativeModel',
    'ForwardContractModel', 
    'SwapModel',  'SwapLegModel',
    'PortfolioModel','PortfolioDerivativeModel','PortfolioCompanyShareModel','PortfolioCompanyShareOptionModel', 'SecurityHoldingModel', 
    'MarketDataModel', 'InstrumentModel',
    'HoldingModel', 'PortfolioHoldingsModel', 'PortfolioCompanyShareHoldingModel','PositionModel','FactorModel','FactorValueModel','FactorDependencyModel',
    'AccountModel', 'OrderModel', 'TransactionModel',
    'ensure_models_registered'
]