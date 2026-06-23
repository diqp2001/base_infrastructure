"""
Repository Factory - Centralized creation and dependency injection for repositories.

This factory manages the creation of local and IBKR repositories with proper dependency injection,
following the Domain-Driven Design principles and eliminating direct parameter passing.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Local repositories
from src.infrastructure.repositories.local_repo.finance.portfolio.company_share_portfolio_option_portfolio_repository import CompanySharePortfolioOptionPortfolioRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.company_share_portfolio_option_repository import CompanySharePortfolioOptionRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.share.company_share.ibkr_company_share_price_return_factor_repository import IBKRCompanySharePriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.share.company_share.ibkr_company_share_avg_turnover_6m_factor_repository import IBKRCompanyShareAvgTurnover6mFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.share.company_share.ibkr_company_share_monthly_price_range_factor_repository import IBKRCompanyShareMonthlyPriceRangeFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.share.company_share.ibkr_company_share_vpt_52w_20d_lag_factor_repository import IBKRCompanyShareVpt52w20dLagFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share.company_share.company_share_price_return_factor_repository import CompanySharePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share.company_share.company_share_factor_repository import CompanyShareFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share.company_share.company_share_avg_turnover_6m_factor_repository import CompanyShareAvgTurnover6mFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share.company_share.company_share_monthly_price_range_factor_repository import CompanyShareMonthlyPriceRangeFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share.company_share.company_share_vpt_52w_20d_lag_factor_repository import CompanyShareVpt52w20dLagFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.share.company_share.ibkr_company_share_factor_repository import IBKRCompanyShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.finance.instrument_repository import IBKRInstrumentRepository
from src.infrastructure.repositories.local_repo.finance.instrument_repository import InstrumentRepository
from src.infrastructure.repositories.local_repo.geographic.sector_repository import SectorRepository
from src.infrastructure.repositories.local_repo.geographic.industry_repository import IndustryRepository
from src.infrastructure.repositories.local_repo.finance.position_repository import PositionRepository
from src.infrastructure.repositories.local_repo.finance.portfolio.portfolio_repository import PortfolioRepository
from src.infrastructure.repositories.local_repo.finance.portfolio.company_share_portfolio_repository import CompanySharePortfolioRepository
from src.infrastructure.repositories.local_repo.finance.portfolio.company_share_option_portfolio_repository import CompanyShareOptionPortfolioRepository
from src.infrastructure.repositories.local_repo.finance.portfolio.derivative_portfolio_repository import DerivativePortfolioRepository
from src.infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.portfolio_holding_repository import PortfolioHoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.company_share_portfolio_holding_repository import CompanySharePortfolioHoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.currency_portfolio_holding_repository import CurrencyPortfolioHoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.company_share_portfolio_portfolio_holding_repository import CompanySharePortfolioPortfolioHoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.currency_portfolio_portfolio_holding_repository import CurrencyPortfolioPortfolioHoldingRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.financial_statement_repository import FinancialStatementRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.income_statement_repository import IncomeStatementRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.balance_sheet_repository import BalanceSheetRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.cash_flow_statement_repository import CashFlowStatementRepository
from src.infrastructure.repositories.local_repo.finance.market_data_repository import MarketDataRepository
from src.infrastructure.repositories.local_repo.finance.order.order_repository import OrderRepository
from src.infrastructure.repositories.local_repo.finance.transaction.transaction_repository import TransactionRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_instrument_factor_repository import IBKRInstrumentFactorRepository
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share.share_factor_repository import ShareFactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_repository import FactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_value_repository import FactorValueRepository
from src.infrastructure.repositories.local_repo.factor.factor_dependency_repository import FactorDependencyRepository

# Local Factor repositories
from src.infrastructure.repositories.local_repo.factor.continent_factor_repository import ContinentFactorRepository
from src.infrastructure.repositories.local_repo.factor.country_factor_repository import CountryFactorRepository

# New Local Factor repositories
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.portfolio_factor_repository import PortfolioFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.company_share_portfolio.company_share_portfolio_correlation_factor_repository import CompanySharePortfolioCorrelationFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.company_share_portfolio.company_share_portfolio_return_factor_repository import CompanySharePortfolioReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.company_share_portfolio.company_share_portfolio_value_factor_repository import CompanySharePortfolioValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.portfolio_value_factor_repository import PortfolioValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.company_share_portfolio.company_share_portfolio_variance_factor_repository import CompanySharePortfolioVarianceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.holding_factor_repository import HoldingFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.company_share_portfolio_holding_factor_repository import CompanySharePortfolioHoldingFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.company_share_portfolio_holding_quantity_factor_repository import CompanySharePortfolioHoldingQuantityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.company_share_portfolio_holding_value_factor_repository import CompanySharePortfolioHoldingValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.company_share_portfolio_holding_weight_factor_repository import CompanySharePortfolioHoldingWeightFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.portfolio_holding_factor_repository import PortfolioHoldingFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.portfolio_holding_value_factor_repository import PortfolioHoldingValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding.company_share_portfolio_portfolio_holding_value_factor_repository import CompanySharePortfolioPortfolioHoldingValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor_repository import CompanyShareOptionGammaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor_repository import CompanyShareOptionRhoFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor_repository import CompanyShareOptionVegaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index.index_factor_repository import IndexFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index.index_price_return_factor_repository import IndexPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.future_price_return_factor_repository import FuturePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor_repository import IndexFuturePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.equity_factor_repository import EquityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.bond_factor_repository import BondFactorRepository
from src.infrastructure.repositories.local_repo.factor.derivative_factor_repository import DerivativeFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.financial_asset_factor_repository import FinancialAssetFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.security_factor_repository import SecurityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.futures_factor_repository import FuturesFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.index_future_factor_repository import IndexFutureFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.index_future_option_factor_repository import IndexFutureOptionFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.index_future_option_price_return_factor_repository import IndexFutureOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.index_future_option_price_factor_repository import IndexFutureOptionPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.future.index_future_option_delta_factor_repository import IndexFutureOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.options_factor_repository import OptionsFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor_repository import CompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_return_factor_repository import CompanySharePortfolioOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_delta_factor_repository import CompanySharePortfolioOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_factor_repository import CompanySharePortfolioOptionPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor_repository import CompanySharePortfolioOptionFactorRepository

from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor_repository import CompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor_repository import CompanyShareOptionFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_factor_repository import CompanyShareOptionPriceFactorRepository

# Advanced Options Pricing Model Repositories - Local
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor_repository import CompanyShareOptionBlackScholesMertonPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_cox_ross_rubinstein_price_factor_repository import CompanyShareOptionCoxRossRubinsteinPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor_repository import CompanyShareOptionHestonPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_hull_white_price_factor_repository import CompanyShareOptionHullWhitePriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_sabr_price_factor_repository import CompanyShareOptionSABRPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_bates_price_factor_repository import CompanyShareOptionBatesPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_dupire_local_volatility_price_factor_repository import CompanyShareOptionDupireLocalVolatilityPriceFactorRepository


from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.cash_repository import CashRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.commodity_repository import CommodityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.crypto_repository import CryptoRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.equity_repository import EquityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.index_future_repository import IndexFutureRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.index_future_option_repository import IndexFutureOptionRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.company_share_option_repository import CompanyShareOptionRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.security_repository import SecurityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.infrastructure.repositories.local_repo.geographic.country_repository import CountryRepository
from src.infrastructure.repositories.local_repo.geographic.continent_repository import ContinentRepository
from src.infrastructure.repositories.local_repo.finance.exchange_repository import ExchangeRepository

# IBKR repositories
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_repository import IBKRFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_portfolio_option_factor_repository import IBKRPortfolioCompanyShareOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_delta_factor_repository import IBKRCompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_factor_repository import IBKRCompanyShareOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_gamma_factor_repository import IBKRCompanyShareOptionGammaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_price_factor_repository import IBKRCompanyShareOptionPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_price_return_factor_repository import IBKRCompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_rho_factor_repository import IBKRCompanyShareOptionRhoFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_vega_factor_repository import IBKRCompanyShareOptionVegaFactorRepository

# Advanced Options Pricing Model Repositories - IBKR
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_black_scholes_merton_price_factor_repository import IBKRCompanyShareOptionBlackScholesMertonPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_cox_ross_rubinstein_price_factor_repository import IBKRCompanyShareOptionCoxRossRubinsteinPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_heston_price_factor_repository import IBKRCompanyShareOptionHestonPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_hull_white_price_factor_repository import IBKRCompanyShareOptionHullWhitePriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_sabr_price_factor_repository import IBKRCompanyShareOptionSABRPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_bates_price_factor_repository import IBKRCompanyShareOptionBatesPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.company_share_option.ibkr_company_share_option_dupire_local_volatility_price_factor_repository import IBKRCompanyShareOptionDupireLocalVolatilityPriceFactorRepository

# IBKR Factor repositories
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_continent_factor_repository import IBKRContinentFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_country_factor_repository import IBKRCountryFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.index.ibkr_index_factor_repository import IBKRIndexFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.index.ibkr_index_price_return_factor_repository import IBKRIndexPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.future.index_future.ibkr_index_future_price_return_factor_repository import IBKRIndexFuturePriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_share_factor_repository import IBKRShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_currency_factor_repository import IBKRCurrencyFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_equity_factor_repository import IBKREquityFactorRepository

# New IBKR Factor repositories
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_portfolio_factor_repository import IBKRPortfolioFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_portfolio_correlation_factor_repository import IBKRCompanySharePortfolioCorrelationFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_bond_factor_repository import IBKRBondFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.ibkr_derivative_factor_repository import IBKRDerivativeFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.future.ibkr_future_factor_repository import IBKRFutureFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.future.index_future.ibkr_index_future_factor_repository import IBKRIndexFutureFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.index_future_option.ibkr_index_future_option_factor_repository import IBKRIndexFutureOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.index_future_option.ibkr_index_future_option_price_return_factor_repository import IBKRIndexFutureOptionPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.index_future_option.ibkr_index_future_option_price_factor_repository import IBKRIndexFutureOptionPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.index_future_option.ibkr_index_future_option_delta_factor_repository import IBKRIndexFutureOptionDeltaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.derivatives.option.ibkr_option_factor_repository import IBKROptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_financial_asset_factor_repository import IBKRFinancialAssetFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_security_factor_repository import IBKRSecurityFactorRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.bond_repository import IBKRBondRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.cash_repository import IBKRCashRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.commodity_repository import IBKRCommodityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.company_share_repository import IBKRCompanyShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.crypto_repository import IBKRCryptoRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.currency_repository import IBKRCurrencyRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.equity_repository import IBKREquityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.derivatives.future.index_future_repository import IBKRIndexFutureRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.derivatives.option.index_future_option_repository import IBKRIndexFutureOptionRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.derivatives.option.company_share_option_repository import IBKRCompanyShareOptionRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.security_repository import IBKRSecurityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.share_repository import IBKRShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.country_repository import IBKRCountryRepository
from src.infrastructure.repositories.ibkr_repo.finance.continent_repository import IBKRContinentRepository
from src.infrastructure.repositories.ibkr_repo.finance.exchange_repository import IBKRExchangeRepository
from src.infrastructure.repositories.ibkr_repo.finance.company_repository import IBKRCompanyRepository
from src.infrastructure.repositories.ibkr_repo.finance.industry_repository import IBKRIndustryRepository
from src.infrastructure.repositories.ibkr_repo.finance.sector_repository import IBKRSectorRepository

# New Position, Transaction, and Order factor repositories
from src.infrastructure.repositories.local_repo.factor.finance.position.company_share_position_value_factor_repository import CompanySharePositionValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.transaction.company_share_transaction_value_factor_repository import CompanyShareTransactionValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.order.company_share_order_quantity_factor_repository import CompanyShareOrderQuantityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.order.company_share_order_price_factor_repository import CompanyShareOrderPriceFactorRepository


class RepositoryFactory:
    """
    Factory for creating and managing repository instances with proper dependency injection.
    
    This factory centralizes repository creation and manages dependencies between repositories,
    providing clean separation of concerns and making IBKR client optional.
    """

    def __init__(self, session: Session, ibkr_client=None):
        """
        Initialize repository factory.
        
        Args:
            session: SQLAlchemy session for database operations
            ibkr_client: Optional Interactive Brokers API client
        """
        self.session = session
        self.ibkr_client = ibkr_client
        self._local_repositories = {}
        self._ibkr_repositories = {}
        self.create_local_repositories()
        if ibkr_client:
            self.create_ibkr_repositories()

    def create_local_repositories(self) -> Dict[str, Any]:
        """
        Create and cache local repository instances.
        
        Returns:
            Dictionary mapping repository names to instances
        """
        if not self._local_repositories:
            self._local_repositories = {
                'Instrument': InstrumentRepository(self.session, factory=self),
                'FactorValue': FactorValueRepository(self.session, factory=self),
                'Factor': FactorRepository(self.session, factory=self),
                'FactorDependency': FactorDependencyRepository(self.session),
                'FinancialAsset': FinancialAssetRepository(self.session, factory=self),
                # Individual factor repositories
                'ContinentFactor': ContinentFactorRepository(self.session, factory=self),
                'CountryFactor': CountryFactorRepository(self.session, factory=self),
                'IndexFactor': IndexFactorRepository(self.session, factory=self),
                'IndexPriceReturnFactor': IndexPriceReturnFactorRepository(self.session, factory=self),
                'FuturePriceReturnFactor': FuturePriceReturnFactorRepository(self.session, factory=self),
                'IndexFuturePriceReturnFactor': IndexFuturePriceReturnFactorRepository(self.session, factory=self),
                'ShareFactor': ShareFactorRepository(self.session, factory=self),
                'CurrencyFactor': CurrencyFactorRepository(self.session, factory=self),
                'EquityFactor': EquityFactorRepository(self.session, factory=self),
                'BondFactor': BondFactorRepository(self.session, factory=self),
                'DerivativeFactor': DerivativeFactorRepository(self.session, factory=self),
                'FinancialAssetFactor': FinancialAssetFactorRepository(self.session, factory=self),
                'SecurityFactor': SecurityFactorRepository(self.session, factory=self),
                'FutureFactor': FuturesFactorRepository(self.session, factory=self),
                'IndexFutureFactor': IndexFutureFactorRepository(self.session, factory=self),
                'IndexFutureOptionFactor': IndexFutureOptionFactorRepository(self.session, factory=self),
                'IndexFutureOptionPriceReturnFactor': IndexFutureOptionPriceReturnFactorRepository(self.session, factory=self),
                'IndexFutureOptionPriceFactor': IndexFutureOptionPriceFactorRepository(self.session, factory=self),
                'IndexFutureOptionDeltaFactor': IndexFutureOptionDeltaFactorRepository(self.session, factory=self),
                'OptionFactor': OptionsFactorRepository(self.session, factory=self),
                'CompanyShareOptionPriceReturnFactor': CompanyShareOptionPriceReturnFactorRepository(self.session, factory=self),
                'CompanySharePortfolioOptionPriceReturnFactor': CompanySharePortfolioOptionPriceReturnFactorRepository(self.session, factory=self),
                'CompanySharePortfolioOptionDeltaFactor': CompanySharePortfolioOptionDeltaFactorRepository(self.session, factory=self),
                'CompanySharePortfolioOptionPriceFactor': CompanySharePortfolioOptionPriceFactorRepository(self.session, factory=self),
                'CompanySharePortfolioOptionFactor': CompanySharePortfolioOptionFactorRepository(self.session, factory=self),
                'CompanySharePortfolioOption': CompanySharePortfolioOptionRepository(self.session, factory=self),
                'CompanyShareOptionDeltaFactor': CompanyShareOptionDeltaFactorRepository(self.session, factory=self),
                'CompanyShareOptionFactor': CompanyShareOptionFactorRepository(self.session, factory=self),
                'CompanyShareOptionPriceFactor': CompanyShareOptionPriceFactorRepository(self.session, factory=self),
                # New factor repositories
                'PortfolioFactor': PortfolioFactorRepository(self.session, factory=self),
                'CompanySharePortfolioCorrelationFactor': CompanySharePortfolioCorrelationFactorRepository(self.session, factory=self),
                'CompanySharePortfolioReturnFactor': CompanySharePortfolioReturnFactorRepository(self.session, factory=self),
                'CompanySharePortfolioValueFactor': CompanySharePortfolioValueFactorRepository(self.session, factory=self),
                'PortfolioValueFactor': PortfolioValueFactorRepository(self.session, factory=self),
                'CompanySharePortfolioVarianceFactor': CompanySharePortfolioVarianceFactorRepository(self.session, factory=self),
                'HoldingFactor': HoldingFactorRepository(self.session, factory=self),
                'CompanySharePortfolioHoldingFactor': CompanySharePortfolioHoldingFactorRepository(self.session, factory=self),
                'CompanySharePortfolioHoldingQuantityFactor': CompanySharePortfolioHoldingQuantityFactorRepository(self.session, factory=self),
                'CompanySharePortfolioHoldingValueFactor': CompanySharePortfolioHoldingValueFactorRepository(self.session, factory=self),
                'CompanySharePortfolioHoldingWeightFactor': CompanySharePortfolioHoldingWeightFactorRepository(self.session, factory=self),
                'PortfolioHoldingFactor': PortfolioHoldingFactorRepository(self.session, factory=self),
                'PortfolioHoldingValueFactor': PortfolioHoldingValueFactorRepository(self.session, factory=self),
                'CompanySharePortfolioPortfolioHoldingValueFactor': CompanySharePortfolioPortfolioHoldingValueFactorRepository(self.session, factory=self),

                # Position, Transaction, and Order factor repositories
                'CompanySharePositionValueFactor': CompanySharePositionValueFactorRepository(self.session, factory=self),
                'CompanyShareTransactionValueFactor': CompanyShareTransactionValueFactorRepository(self.session, factory=self),
                'CompanyShareOrderQuantityFactor': CompanyShareOrderQuantityFactorRepository(self.session, factory=self),
                'CompanyShareOrderPriceFactor': CompanyShareOrderPriceFactorRepository(self.session, factory=self),

                'CompanyShareOptionGammaFactor': CompanyShareOptionGammaFactorRepository(self.session, factory=self),
                'CompanyShareOptionRhoFactor': CompanyShareOptionRhoFactorRepository(self.session, factory=self),
                'CompanyShareOptionVegaFactor': CompanyShareOptionVegaFactorRepository(self.session, factory=self),

                # Advanced Options Pricing Model Repositories
                'CompanyShareOptionBlackScholesMertonPriceFactor': CompanyShareOptionBlackScholesMertonPriceFactorRepository(self.session, factory=self),
                'CompanyShareOptionCoxRossRubinsteinPriceFactor': CompanyShareOptionCoxRossRubinsteinPriceFactorRepository(self.session, factory=self),
                'CompanyShareOptionHestonPriceFactor': CompanyShareOptionHestonPriceFactorRepository(self.session, factory=self),
                'CompanyShareOptionHullWhitePriceFactor': CompanyShareOptionHullWhitePriceFactorRepository(self.session, factory=self),
                'CompanyShareOptionSabrPriceFactor': CompanyShareOptionSABRPriceFactorRepository(self.session, factory=self),
                'CompanyShareOptionBatesPriceFactor': CompanyShareOptionBatesPriceFactorRepository(self.session, factory=self),
                'CompanyShareOptionDupireLocalVolatilityPriceFactor': CompanyShareOptionDupireLocalVolatilityPriceFactorRepository(self.session, factory=self),

                'IndexFuture': IndexFutureRepository(self.session, factory=self),
                'IndexFutureOption': IndexFutureOptionRepository(self.session, factory=self),
                'CompanyShareOption': CompanyShareOptionRepository(self.session, factory=self),
                'CompanySharePortfolioOptionPortfolio': CompanySharePortfolioOptionPortfolioRepository(self.session, factory=self),
                'CompanyShareOptionPortfolio': CompanyShareOptionPortfolioRepository(self.session, factory=self),
                'CompanySharePortfolio': CompanySharePortfolioRepository(self.session, factory=self),
                'DerivativePortfolio': DerivativePortfolioRepository(self.session, factory=self),
                'CompanyShare': CompanyShareRepository(self.session, factory=self),
                'CompanyShareFactor': CompanyShareFactorRepository(self.session, factory=self),
                'CompanySharePriceReturnFactor': CompanySharePriceReturnFactorRepository(self.session, factory=self),
                'CompanyShareAvgTurnover6mFactor': CompanyShareAvgTurnover6mFactorRepository(self.session, factory=self),
                'CompanyShareMonthlyPriceRangeFactor': CompanyShareMonthlyPriceRangeFactorRepository(self.session, factory=self),
                'CompanyShareVpt52w20dLagFactor': CompanyShareVpt52w20dLagFactorRepository(self.session, factory=self),
                'Currency': CurrencyRepository(self.session, factory=self),
                'Bond': BondRepository(self.session, factory=self),
                'Index': IndexRepository(self.session, factory=self),
                'Crypto': CryptoRepository(self.session, factory=self),
                'Commodity': CommodityRepository(self.session, factory=self),
                'Cash': CashRepository(self.session, factory=self),
                'Equity': EquityRepository(self.session, factory=self),
                'Share': ShareRepository(self.session, factory=self),
                'Security': SecurityRepository(self.session, factory=self),
                'Country': CountryRepository(self.session, factory=self),
                'Continent': ContinentRepository(self.session, factory=self),
                'Exchange': ExchangeRepository(self.session, factory=self),
                # Additional geographic repositories
                'Sector': SectorRepository(self.session, factory=self),
                'Industry': IndustryRepository(self.session, factory=self),
                # Portfolio and position repositories
                'Position': PositionRepository(self.session, factory=self),
                'Portfolio': PortfolioRepository(self.session, factory=self),
                'Company': CompanyRepository(self.session, factory=self),

                # Holding repositories
                'Holding': HoldingRepository(self.session, factory=self),
                'PortfolioHolding': PortfolioHoldingRepository(self.session, factory=self),
                'CompanySharePortfolioHolding': CompanySharePortfolioHoldingRepository(self.session, factory=self),
                'CurrencyPortfolioHolding': CurrencyPortfolioHoldingRepository(self.session, factory=self),
                'CompanySharePortfolioPortfolioHolding': CompanySharePortfolioPortfolioHoldingRepository(self.session, factory=self),
                'CurrencyPortfolioPortfolioHolding': CurrencyPortfolioPortfolioHoldingRepository(self.session, factory=self),
                # Financial statement repositories
                'FinancialStatement': FinancialStatementRepository(self.session, factory=self),
                'IncomeStatement': IncomeStatementRepository(self.session, factory=self),
                'BalanceSheet': BalanceSheetRepository(self.session, factory=self),
                'CashFlowStatement': CashFlowStatementRepository(self.session, factory=self),
                # Market data repository
                'MarketData': MarketDataRepository(self.session, factory=self),
                # Order and transaction repositories
                'Order': OrderRepository(self.session, factory=self),
                'Transaction': TransactionRepository(self.session, factory=self)
            }
        return self._local_repositories

    def create_ibkr_repositories(self, ibkr_client=None) -> Optional[Dict[str, Any]]:
        """
        Create and cache IBKR repository instances if IBKR client is available.
        
        Args:
            ibkr_client: Optional IBKR client override
            
        Returns:
            Dictionary mapping repository names to IBKR instances, or None if no client
        """
        # Use provided client or factory default
        client = ibkr_client or self.ibkr_client
        
        if not client:
            client = self.create_ibkr_client()
            return None

        if not self._ibkr_repositories:
            self._ibkr_repositories = {
                'InstrumentFactor': IBKRInstrumentFactorRepository(ibkr_client=client, factory=self),
                'Instrument': IBKRInstrumentRepository(ibkr_client=client, factory=self),
                'Factor': IBKRFactorRepository(ibkr_client=client, factory=self),
                'FactorValue': IBKRFactorValueRepository(ibkr_client=client, factory=self),
                # Individual factor repositories
                'ContinentFactor': IBKRContinentFactorRepository(ibkr_client=client, factory=self),
                'CountryFactor': IBKRCountryFactorRepository(ibkr_client=client, factory=self),
                'IndexFactor': IBKRIndexFactorRepository(ibkr_client=client, factory=self),
                'IndexPriceReturnFactor': IBKRIndexPriceReturnFactorRepository(ibkr_client=client, factory=self),
                'IndexFuturePriceReturnFactor': IBKRIndexFuturePriceReturnFactorRepository(ibkr_client=client, factory=self),
                'ShareFactor': IBKRShareFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareFactor': IBKRCompanyShareFactorRepository(ibkr_client=client, factory=self),
                'CompanySharePriceReturnFactor': IBKRCompanySharePriceReturnFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareAvgTurnover6mFactor': IBKRCompanyShareAvgTurnover6mFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareMonthlyPriceRangeFactor': IBKRCompanyShareMonthlyPriceRangeFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareVpt52w20dLagFactor': IBKRCompanyShareVpt52w20dLagFactorRepository(ibkr_client=client, factory=self),
                'PortfolioCompanyShareOptionFactor': IBKRPortfolioCompanyShareOptionFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionDeltaFactor': IBKRCompanyShareOptionDeltaFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionFactor': IBKRCompanyShareOptionFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionGammaFactor': IBKRCompanyShareOptionGammaFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionPriceFactor': IBKRCompanyShareOptionPriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionPriceReturnFactor': IBKRCompanyShareOptionPriceReturnFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionRhoFactor': IBKRCompanyShareOptionRhoFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionVegaFactor': IBKRCompanyShareOptionVegaFactorRepository(ibkr_client=client, factory=self),
                # Advanced Options Pricing Model Repositories - IBKR
                'CompanyShareOptionBlackScholesMertonPriceFactor': IBKRCompanyShareOptionBlackScholesMertonPriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionCoxRossRubinsteinPriceFactor': IBKRCompanyShareOptionCoxRossRubinsteinPriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionHestonPriceFactor': IBKRCompanyShareOptionHestonPriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionHullWhitePriceFactor': IBKRCompanyShareOptionHullWhitePriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionSabrPriceFactor': IBKRCompanyShareOptionSABRPriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionBatesPriceFactor': IBKRCompanyShareOptionBatesPriceFactorRepository(ibkr_client=client, factory=self),
                'CompanyShareOptionDupireLocalVolatilityPriceFactor': IBKRCompanyShareOptionDupireLocalVolatilityPriceFactorRepository(ibkr_client=client, factory=self),
                'CurrencyFactor': IBKRCurrencyFactorRepository(ibkr_client=client, factory=self),
                'EquityFactor': IBKREquityFactorRepository(ibkr_client=client, factory=self),
                # New IBKR factor repositories
                'BondFactor': IBKRBondFactorRepository(ibkr_client=client, factory=self),
                'DerivativeFactor': IBKRDerivativeFactorRepository(ibkr_client=client, factory=self),
                'FutureFactor': IBKRFutureFactorRepository(ibkr_client=client, factory=self),
                'IndexFutureFactor': IBKRIndexFutureFactorRepository(ibkr_client=client, factory=self),
                'IndexFutureOptionFactor': IBKRIndexFutureOptionFactorRepository(ibkr_client=client, factory=self),
                'IndexFutureOptionPriceReturnFactor': IBKRIndexFutureOptionPriceReturnFactorRepository(ibkr_client=client, factory=self),
                'IndexFutureOptionPriceFactor': IBKRIndexFutureOptionPriceFactorRepository(ibkr_client=client, factory=self),
                'IndexFutureOptionDeltaFactor': IBKRIndexFutureOptionDeltaFactorRepository(ibkr_client=client, factory=self),
                'OptionFactor': IBKROptionFactorRepository(ibkr_client=client, factory=self),
                'FinancialAssetFactor': IBKRFinancialAssetFactorRepository(ibkr_client=client, factory=self),
                'SecurityFactor': IBKRSecurityFactorRepository(ibkr_client=client, factory=self),
                'PortfolioFactor': IBKRPortfolioFactorRepository(ibkr_client=client, factory=self),
                'CompanySharePortfolioCorrelationFactor': IBKRCompanySharePortfolioCorrelationFactorRepository(ibkr_client=client, factory=self),
                'IndexFuture': IBKRIndexFutureRepository(ibkr_client=client, factory=self),
                'IndexFutureOption': IBKRIndexFutureOptionRepository(ibkr_client=client, factory=self),
                'CompanyShareOption': IBKRCompanyShareOptionRepository(ibkr_client=client, factory=self),
                'CompanyShare': IBKRCompanyShareRepository(ibkr_client=client, factory=self),
                'Currency': IBKRCurrencyRepository(ibkr_client=client, factory=self),
                'Bond': IBKRBondRepository(ibkr_client=client, factory=self),
                'Index': IBKRIndexRepository(ibkr_client=client, factory=self),
                'Crypto': IBKRCryptoRepository(ibkr_client=client, factory=self),
                'Commodity': IBKRCommodityRepository(ibkr_client=client, factory=self),
                'Cash': IBKRCashRepository(ibkr_client=client, factory=self),
                'Equity': IBKREquityRepository(ibkr_client=client, factory=self),
                'Share': IBKRShareRepository(ibkr_client=client, factory=self),
                'Security': IBKRSecurityRepository(ibkr_client=client, factory=self),
                'Country': IBKRCountryRepository(ibkr_client=client, factory=self),
                'Continent': IBKRContinentRepository(ibkr_client=client, factory=self),
                'Exchange': IBKRExchangeRepository(ibkr_client=client, factory=self),
                'Company': IBKRCompanyRepository(ibkr_client=client, factory=self),
                'Industry': IBKRIndustryRepository(ibkr_client=client, factory=self),
                'Sector': IBKRSectorRepository(ibkr_client=client, factory=self)
            }
        return self._ibkr_repositories

    def create_ibkr_client(self) -> Optional[Any]:
        """
        Create IBKR client using broker factory if not already provided.
        
        Returns:
            IBKR client instance or None if creation failed
        """
        if self.ibkr_client:
            return self.ibkr_client
            
        try:
            from src.application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker
            
            ib_config = {
                'host': "127.0.0.1",
                'port': 7497,
                'client_id': 1,
                'timeout': 60,
                'account_id': 'DEFAULT',
                'enable_logging': True,
                'max_import_ibkr': True,
            }
            
            client = create_interactive_brokers_broker(**ib_config)
            client.connect()
            
            self.ibkr_client = client
            return client
            
        except Exception as e:
            print(f"Error creating IBKR client: {e}")
            return None

    def get_local_repository(self, entity_class_or_key):
        """
        Get local repository by string key or by domain entity class.
        String keys accept CamelCase ('CompanyShare'), snake_case ('company_share'),
        or mapper discriminator values ('CurrencyPortfolioPortfolioHoldings').
        """
        repos = self.create_local_repositories()
        if isinstance(entity_class_or_key, str):
            result = repos.get(entity_class_or_key)
            if result is not None:
                return result
            camel = ''.join(w.capitalize() for w in entity_class_or_key.split('_'))
            result = repos.get(camel)
            if result is not None:
                return result
            # Fallback: match by mapper.discriminator (e.g. holding_type values stored in DB)
            for repo in repos.values():
                m_disc = getattr(getattr(repo, 'mapper', None), 'discriminator', None)
                if m_disc is not None and (m_disc == entity_class_or_key or m_disc == camel):
                    return repo
            return None
        for repo in repos.values():
            if hasattr(repo, 'entity_class') and repo.entity_class is entity_class_or_key:
                return repo
        return None

    def get_local_repository_by_discriminator(self, discriminator: str):
        """
        Get local repository whose mapper.discriminator matches the given value.
        Accepts both snake_case DB values ('company_share_portfolio_holdings') and
        CamelCase mapper discriminators ('CompanySharePortfolioHoldings').
        """
        repos = self.create_local_repositories()
        camel = ''.join(w.capitalize() for w in discriminator.split('_'))
        for repo in repos.values():
            m_disc = getattr(getattr(repo, 'mapper', None), 'discriminator', None)
            if m_disc is not None and (m_disc == discriminator or m_disc == camel):
                return repo
        return None

    def get_ibkr_repository(self, entity_class_or_key):
        """
        Get IBKR repository by string key or by domain entity class.
        String keys accept CamelCase ('CompanyShare') or snake_case ('company_share').
        """
        repos = self.create_ibkr_repositories()
        if not repos:
            return None
        if isinstance(entity_class_or_key, str):
            result = repos.get(entity_class_or_key)
            if result is not None:
                return result
            camel = ''.join(w.capitalize() for w in entity_class_or_key.split('_'))
            return repos.get(camel)
        for repo in repos.values():
            if hasattr(repo, 'entity_class') and repo.entity_class is entity_class_or_key:
                return repo
        return None

    def has_ibkr_client(self) -> bool:
        """Check if IBKR client is available."""
        return self.ibkr_client is not None
    
    @property
    def instrument_local_repo(self):
        """Get instrument repository for dependency injection."""
        return self.get_local_repository('Instrument')
    
    @property
    def financial_asset_local_repo(self):
        """Get financial_asset repository for dependency injection."""
        return self.get_local_repository('FinancialAsset')
    
    @property
    def factor_value_local_repo(self):
        """Get factor_value repository for dependency injection."""
        return self.get_local_repository('FactorValue')


    @property
    def factor_local_repo(self):
        """Get factor repository for dependency injection."""
        return self.get_local_repository('Factor')

    @property
    def factor_dependency_local_repo(self):
        """Get factor_dependency repository for dependency injection."""
        return self.get_local_repository('FactorDependency')

    # Individual local factor repositories
    @property
    def continent_factor_local_repo(self):
        """Get continent_factor repository for dependency injection."""
        return self.get_local_repository('ContinentFactor')

    @property
    def country_factor_local_repo(self):
        """Get country_factor repository for dependency injection."""
        return self.get_local_repository('CountryFactor')

    @property
    def index_factor_local_repo(self):
        """Get index_factor repository for dependency injection."""
        return self.get_local_repository('IndexFactor')

    @property
    def index_price_return_factor_local_repo(self):
        """Get index_price_return_factor repository for dependency injection."""
        return self.get_local_repository('IndexPriceReturnFactor')

    @property
    def currency_factor_local_repo(self):
        """Get currency_factor repository for dependency injection."""
        return self.get_local_repository('CurrencyFactor')

    @property
    def equity_factor_local_repo(self):
        """Get equity_factor repository for dependency injection."""
        return self.get_local_repository('EquityFactor')

    @property
    def bond_factor_local_repo(self):
        """Get bond_factor repository for dependency injection."""
        return self.get_local_repository('BondFactor')

    @property
    def derivative_factor_local_repo(self):
        """Get derivative_factor repository for dependency injection."""
        return self.get_local_repository('DerivativeFactor')

    @property
    def financial_asset_factor_local_repo(self):
        """Get financial_asset_factor repository for dependency injection."""
        return self.get_local_repository('FinancialAssetFactor')

    @property
    def security_factor_local_repo(self):
        """Get security_factor repository for dependency injection."""
        return self.get_local_repository('SecurityFactor')

    @property
    def future_factor_local_repo(self):
        """Get future_factor repository for dependency injection."""
        return self.get_local_repository('FutureFactor')

    @property
    def index_future_factor_local_repo(self):
        """Get index_future_factor repository for dependency injection."""
        return self.get_local_repository('IndexFutureFactor')

    @property
    def option_factor_local_repo(self):
        """Get option_factor repository for dependency injection."""
        return self.get_local_repository('OptionFactor')


    @property
    def base_factor_local_repo(self):
        """Get base_factor repository for dependency injection."""
        return self.get_local_repository('BaseFactor')


    @property
    def share_factor_local_repo(self):
        """Get share_factor repository for dependency injection."""
        return self.get_local_repository('ShareFactor')


    @property
    def index_future_local_repo(self):
        """Get index_future repository for dependency injection."""
        return self.get_local_repository('IndexFuture')

    @property
    def index_future_option_local_repo(self):
        """Get index_future_option repository for dependency injection."""
        return self.get_local_repository('IndexFutureOption')

    @property
    def index_future_option_factor_local_repo(self):
        """Get index_future_option_factor repository for dependency injection."""
        return self.get_local_repository('IndexFutureOptionFactor')

    @property
    def index_future_option_price_return_factor_local_repo(self):
        """Get index_future_option_price_return_factor repository for dependency injection."""
        return self.get_local_repository('IndexFutureOptionPriceReturnFactor')

    @property
    def index_future_option_price_factor_local_repo(self):
        """Get index_future_option_price_factor repository for dependency injection."""
        return self.get_local_repository('IndexFutureOptionPriceFactor')

    @property
    def index_future_option_delta_factor_local_repo(self):
        """Get index_future_option_delta_factor repository for dependency injection."""
        return self.get_local_repository('IndexFutureOptionDeltaFactor')

    @property
    def company_share_local_repo(self):
        """Get company_share repository for dependency injection."""
        return self.get_local_repository('CompanyShare')


    @property
    def currency_local_repo(self):
        """Get currency repository for dependency injection."""
        return self.get_local_repository('Currency')


    @property
    def bond_local_repo(self):
        """Get bond repository for dependency injection."""
        return self.get_local_repository('Bond')


    @property
    def index_local_repo(self):
        """Get index repository for dependency injection."""
        return self.get_local_repository('Index')


    @property
    def crypto_local_repo(self):
        """Get crypto repository for dependency injection."""
        return self.get_local_repository('Crypto')


    @property
    def commodity_local_repo(self):
        """Get commodity repository for dependency injection."""
        return self.get_local_repository('Commodity')


    @property
    def cash_local_repo(self):
        """Get cash repository for dependency injection."""
        return self.get_local_repository('Cash')


    @property
    def equity_local_repo(self):
        """Get equity repository for dependency injection."""
        return self.get_local_repository('Equity')


    @property
    def etf_share_local_repo(self):
        """Get etf_share repository for dependency injection."""
        return self.get_local_repository('EtfShare')


    @property
    def share_local_repo(self):
        """Get share repository for dependency injection."""
        return self.get_local_repository('Share')


    @property
    def security_local_repo(self):
        """Get security repository for dependency injection."""
        return self.get_local_repository('Security')

    @property
    def country_local_repo(self):
        """Get country repository for dependency injection."""
        return self.get_local_repository('Country')

    @property
    def continent_local_repo(self):
        """Get continent repository for dependency injection."""
        return self.get_local_repository('Continent')

    @property
    def exchange_local_repo(self):
        """Get exchange repository for dependency injection."""
        return self.get_local_repository('Exchange')

    @property
    def instrument_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self.get_ibkr_repository('Instrument')
    @property
    def instrument_factor_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self.get_ibkr_repository('InstrumentFactor')
    @property
    def factor_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self.get_ibkr_repository('Factor')


    @property
    def factor_value_ibkr_repo(self):
        """Get factor_value repository for dependency injection."""
        return self.get_ibkr_repository('FactorValue')

    # Individual IBKR factor repositories
    @property
    def continent_factor_ibkr_repo(self):
        """Get continent_factor repository for dependency injection."""
        return self.get_ibkr_repository('ContinentFactor')

    @property
    def country_factor_ibkr_repo(self):
        """Get country_factor repository for dependency injection."""
        return self.get_ibkr_repository('CountryFactor')

    @property
    def index_factor_ibkr_repo(self):
        """Get index_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFactor')

    @property
    def index_price_return_factor_ibkr_repo(self):
        """Get index_price_return_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexPriceReturnFactor')

    @property
    def index_future_price_return_factor_ibkr_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFuturePriceReturnFactor')

    @property
    def share_factor_ibkr_repo(self):
        """Get share_factor repository for dependency injection."""
        return self.get_ibkr_repository('ShareFactor')

    @property
    def currency_factor_ibkr_repo(self):
        """Get currency_factor repository for dependency injection."""
        return self.get_ibkr_repository('CurrencyFactor')

    @property
    def equity_factor_ibkr_repo(self):
        """Get equity_factor repository for dependency injection."""
        return self.get_ibkr_repository('EquityFactor')


    @property
    def index_future_ibkr_repo(self):
        """Get index_future repository for dependency injection."""
        return self.get_ibkr_repository('IndexFuture')

    @property
    def index_future_option_ibkr_repo(self):
        """Get index_future_option repository for dependency injection."""
        return self.get_ibkr_repository('IndexFutureOption')

    @property
    def index_future_option_factor_ibkr_repo(self):
        """Get index_future_option_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFutureOptionFactor')

    @property
    def index_future_option_price_return_factor_ibkr_repo(self):
        """Get index_future_option_price_return_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFutureOptionPriceReturnFactor')

    @property
    def index_future_option_price_factor_ibkr_repo(self):
        """Get index_future_option_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFutureOptionPriceFactor')

    @property
    def index_future_option_delta_factor_ibkr_repo(self):
        """Get index_future_option_delta_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFutureOptionDeltaFactor')

    @property
    def company_share_ibkr_repo(self):
        """Get company_share repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShare')


    @property
    def currency_ibkr_repo(self):
        """Get currency repository for dependency injection."""
        return self.get_ibkr_repository('Currency')


    @property
    def bond_ibkr_repo(self):
        """Get bond repository for dependency injection."""
        return self.get_ibkr_repository('Bond')


    @property
    def index_ibkr_repo(self):
        """Get index repository for dependency injection."""
        return self.get_ibkr_repository('Index')


    @property
    def crypto_ibkr_repo(self):
        """Get crypto repository for dependency injection."""
        return self.get_ibkr_repository('Crypto')


    @property
    def commodity_ibkr_repo(self):
        """Get commodity repository for dependency injection."""
        return self.get_ibkr_repository('Commodity')


    @property
    def cash_ibkr_repo(self):
        """Get cash repository for dependency injection."""
        return self.get_ibkr_repository('Cash')


    @property
    def equity_ibkr_repo(self):
        """Get equity repository for dependency injection."""
        return self.get_ibkr_repository('Equity')


    @property
    def etf_share_ibkr_repo(self):
        """Get etf_share repository for dependency injection."""
        return self.get_ibkr_repository('EtfShare')


    @property
    def share_ibkr_repo(self):
        """Get share repository for dependency injection."""
        return self.get_ibkr_repository('Share')


    @property
    def security_ibkr_repo(self):
        """Get security repository for dependency injection."""
        return self.get_ibkr_repository('Security')

    @property
    def country_ibkr_repo(self):
        """Get country repository for dependency injection."""
        return self.get_ibkr_repository('Country')

    @property
    def continent_ibkr_repo(self):
        """Get continent repository for dependency injection."""
        return self.get_ibkr_repository('Continent')

    @property
    def exchange_ibkr_repo(self):
        """Get exchange repository for dependency injection."""
        return self.get_ibkr_repository('Exchange')

    # New IBKR factor repository properties
    @property
    def bond_factor_ibkr_repo(self):
        """Get bond_factor repository for dependency injection."""
        return self.get_ibkr_repository('BondFactor')

    @property
    def derivative_factor_ibkr_repo(self):
        """Get derivative_factor repository for dependency injection."""
        return self.get_ibkr_repository('DerivativeFactor')

    @property
    def future_factor_ibkr_repo(self):
        """Get future_factor repository for dependency injection."""
        return self.get_ibkr_repository('FutureFactor')

    @property
    def index_future_factor_ibkr_repo(self):
        """Get index_future_factor repository for dependency injection."""
        return self.get_ibkr_repository('IndexFutureFactor')

    @property
    def option_factor_ibkr_repo(self):
        """Get option_factor repository for dependency injection."""
        return self.get_ibkr_repository('OptionFactor')

    @property
    def financial_asset_factor_ibkr_repo(self):
        """Get financial_asset_factor repository for dependency injection."""
        return self.get_ibkr_repository('FinancialAssetFactor')

    @property
    def security_factor_ibkr_repo(self):
        """Get security_factor repository for dependency injection."""
        return self.get_ibkr_repository('SecurityFactor')
    
    # Additional local repository properties
    @property
    def sector_local_repo(self):
        """Get sector repository for dependency injection."""
        return self.get_local_repository('Sector')
    
    @property
    def industry_local_repo(self):
        """Get industry repository for dependency injection."""
        return self.get_local_repository('Industry')
    
    @property
    def position_local_repo(self):
        """Get position repository for dependency injection."""
        return self.get_local_repository('Position')
    
    @property
    def portfolio_local_repo(self):
        """Get portfolio repository for dependency injection."""
        return self.get_local_repository('Portfolio')
    
    @property
    def company_local_repo(self):
        """Get company repository for dependency injection."""
        return self.get_local_repository('Company')
    
    @property
    def holding_local_repo(self):
        """Get holding repository for dependency injection."""
        return self.get_local_repository('Holding')
    
    @property
    def portfolio_holding_local_repo(self):
        """Get portfolio_holding repository for dependency injection."""
        return self.get_local_repository('PortfolioHolding')
    
    @property
    def company_share_portfolio_holding_local_repo(self):
        """Get portfolio_company_share_holding repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioHolding')
    
    @property
    def financial_statement_local_repo(self):
        """Get financial_statement repository for dependency injection."""
        return self.get_local_repository('FinancialStatement')
    
    @property
    def income_statement_local_repo(self):
        """Get income_statement repository for dependency injection."""
        return self.get_local_repository('IncomeStatement')
    
    @property
    def balance_sheet_local_repo(self):
        """Get balance_sheet repository for dependency injection."""
        return self.get_local_repository('BalanceSheet')
    
    @property
    def cash_flow_statement_local_repo(self):
        """Get cash_flow_statement repository for dependency injection."""
        return self.get_local_repository('CashFlowStatement')
    
    @property
    def market_data_local_repo(self):
        """Get market_data repository for dependency injection."""
        return self.get_local_repository('MarketData')
    
    @property
    def order_local_repo(self):
        """Get order repository for dependency injection."""
        return self.get_local_repository('Order')
    
    @property
    def transaction_local_repo(self):
        """Get transaction repository for dependency injection."""
        return self.get_local_repository('Transaction')
    
    @property
    def future_price_return_factor_local_repo(self):
        """Get future_price_return_factor repository for dependency injection."""
        return self.get_local_repository('FuturePriceReturnFactor')
    
    @property
    def index_future_price_return_factor_local_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self.get_local_repository('IndexFuturePriceReturnFactor')
    
    # Additional IBKR repository properties
    @property
    def company_ibkr_repo(self):
        """Get company repository for dependency injection."""
        return self.get_ibkr_repository('Company')

    @property
    def industry_ibkr_repo(self):
        """Get industry repository for dependency injection."""
        return self.get_ibkr_repository('Industry')

    @property
    def sector_ibkr_repo(self):
        """Get sector repository for dependency injection."""
        return self.get_ibkr_repository('Sector')

    # New local repository properties
    @property
    def portfolio_factor_local_repo(self):
        """Get portfolio_factor repository for dependency injection."""
        return self.get_local_repository('PortfolioFactor')
    
    @property
    def company_share_portfolio_correlation_factor_local_repo(self):
        """Get portfolio_company_share_correlation_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioCorrelationFactor')
    
    @property
    def company_share_portfolio_return_factor_local_repo(self):
        """Get portfolio_company_share_return_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioReturnFactor')
    
    @property
    def company_share_portfolio_value_factor_local_repo(self):
        """Get portfolio_company_share_value_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioValueFactor')
    
    @property
    def portfolio_value_factor_local_repo(self):
        """Get portfolio_value_factor repository for dependency injection."""
        return self.get_local_repository('PortfolioValueFactor')
    
    @property
    def company_share_portfolio_variance_factor_local_repo(self):
        """Get portfolio_company_share_variance_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioVarianceFactor')
    
    @property
    def holding_factor_local_repo(self):
        """Get holding_factor repository for dependency injection."""
        return self.get_local_repository('HoldingFactor')
    
    @property
    def company_share_portfolio_holding_factor_local_repo(self):
        """Get portfolio_company_share_holding_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioHoldingFactor')
    
    @property
    def company_share_portfolio_holding_quantity_factor_local_repo(self):
        """Get portfolio_company_share_holding_quantity_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioHoldingQuantityFactor')
    
    @property
    def company_share_portfolio_holding_value_factor_local_repo(self):
        """Get portfolio_company_share_holding_value_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioHoldingValueFactor')
    
    @property
    def company_share_portfolio_holding_weight_factor_local_repo(self):
        """Get portfolio_company_share_holding_weight_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioHoldingWeightFactor')
    
    @property
    def portfolio_holding_factor_local_repo(self):
        """Get portfolio_holding_factor repository for dependency injection."""
        return self.get_local_repository('PortfolioHoldingFactor')
    
    @property
    def portfolio_holding_value_factor_local_repo(self):
        """Get portfolio_holding_value_factor repository for dependency injection."""
        return self.get_local_repository('PortfolioHoldingValueFactor')

    @property
    def company_share_portfolio_portfolio_holding_value_factor_local_repo(self):
        """Get company_share_portfolio_portfolio_holding_value_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioPortfolioHoldingValueFactor')

    # Position, Transaction, and Order factor repositories
    @property
    def company_share_position_value_factor_local_repo(self):
        """Get company_share_position_value_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePositionValueFactor')
    
    @property
    def company_share_transaction_value_factor_local_repo(self):
        """Get company_share_transaction_value_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareTransactionValueFactor')
    
    @property
    def company_share_order_quantity_factor_local_repo(self):
        """Get company_share_order_quantity_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOrderQuantityFactor')
    
    @property
    def company_share_order_price_factor_local_repo(self):
        """Get company_share_order_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOrderPriceFactor')
    
    @property
    def company_share_option_gamma_factor_local_repo(self):
        """Get company_share_option_gamma_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionGammaFactor')
    
    @property
    def company_share_option_rho_factor_local_repo(self):
        """Get company_share_option_rho_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionRhoFactor')
    
    @property
    def company_share_option_vega_factor_local_repo(self):
        """Get company_share_option_vega_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionVegaFactor')

    # Advanced Options Pricing Model Repository Properties
    @property
    def company_share_option_black_scholes_merton_price_factor_local_repo(self):
        """Get company_share_option_black_scholes_merton_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionBlackScholesMertonPriceFactor')
    
    @property
    def company_share_option_cox_ross_rubinstein_price_factor_local_repo(self):
        """Get company_share_option_cox_ross_rubinstein_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionCoxRossRubinsteinPriceFactor')
    
    @property
    def company_share_option_heston_price_factor_local_repo(self):
        """Get company_share_option_heston_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionHestonPriceFactor')
    
    @property
    def company_share_option_hull_white_price_factor_local_repo(self):
        """Get company_share_option_hull_white_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionHullWhitePriceFactor')
    
    @property
    def company_share_option_sabr_price_factor_local_repo(self):
        """Get company_share_option_sabr_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionSabrPriceFactor')
    
    @property
    def company_share_option_bates_price_factor_local_repo(self):
        """Get company_share_option_bates_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionBatesPriceFactor')
    
    @property
    def company_share_option_dupire_local_volatility_price_factor_local_repo(self):
        """Get company_share_option_dupire_local_volatility_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionDupireLocalVolatilityPriceFactor')

    # New IBKR repository properties
    @property
    def portfolio_factor_ibkr_repo(self):
        """Get portfolio_factor repository for dependency injection."""
        return self.get_ibkr_repository('PortfolioFactor')
    
    @property
    def company_share_portfolio_correlation_factor_ibkr_repo(self):
        """Get portfolio_company_share_correlation_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanySharePortfolioCorrelationFactor')

    # New Local repository properties
    @property
    def company_share_portfolio_option_factor_local_repo(self):
        """Get portfolio_company_share_option_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioOptionFactor')

    

    @property
    def company_share_option_delta_factor_local_repo(self):
        """Get company_share_option_delta_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionDeltaFactor')

    @property
    def company_share_option_factor_local_repo(self):
        """Get company_share_option_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionFactor')

    @property
    def company_share_option_price_factor_local_repo(self):
        """Get company_share_option_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionPriceFactor')

    # New IBKR repository properties
    @property
    def company_share_portfolio_option_factor_ibkr_repo(self):
        """Get portfolio_company_share_option_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanySharePortfolioOptionFactor')

 

    @property
    def company_share_option_delta_factor_ibkr_repo(self):
        """Get company_share_option_delta_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionDeltaFactor')

    @property
    def company_share_option_factor_ibkr_repo(self):
        """Get company_share_option_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionFactor')

    @property
    def company_share_option_gamma_factor_ibkr_repo(self):
        """Get company_share_option_gamma_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionGammaFactor')

    @property
    def company_share_option_price_factor_ibkr_repo(self):
        """Get company_share_option_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionPriceFactor')

    @property
    def company_share_option_price_return_factor_ibkr_repo(self):
        """Get company_share_option_price_return_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionPriceReturnFactor')

    @property
    def company_share_option_rho_factor_ibkr_repo(self):
        """Get company_share_option_rho_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionRhoFactor')

    @property
    def company_share_option_vega_factor_ibkr_repo(self):
        """Get company_share_option_vega_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionVegaFactor')

    # Advanced Options Pricing Model IBKR Repository Properties
    @property
    def company_share_option_black_scholes_merton_price_factor_ibkr_repo(self):
        """Get company_share_option_black_scholes_merton_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionBlackScholesMertonPriceFactor')
    
    @property
    def company_share_option_cox_ross_rubinstein_price_factor_ibkr_repo(self):
        """Get company_share_option_cox_ross_rubinstein_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionCoxRossRubinsteinPriceFactor')
    
    @property
    def company_share_option_heston_price_factor_ibkr_repo(self):
        """Get company_share_option_heston_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionHestonPriceFactor')
    
    @property
    def company_share_option_hull_white_price_factor_ibkr_repo(self):
        """Get company_share_option_hull_white_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionHullWhitePriceFactor')
    
    @property
    def company_share_option_sabr_price_factor_ibkr_repo(self):
        """Get company_share_option_sabr_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionSabrPriceFactor')
    
    @property
    def company_share_option_bates_price_factor_ibkr_repo(self):
        """Get company_share_option_bates_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionBatesPriceFactor')
    
    @property
    def company_share_option_dupire_local_volatility_price_factor_ibkr_repo(self):
        """Get company_share_option_dupire_local_volatility_price_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareOptionDupireLocalVolatilityPriceFactor')

    # Missing properties for already registered repositories
    @property
    def company_share_factor_local_repo(self):
        """Get company_share_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareFactor')

    @property
    def company_share_price_return_factor_local_repo(self):
        """Get company_share_price_return_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePriceReturnFactor')

    @property
    def company_share_option_local_repo(self):
        """Get company_share_option repository for dependency injection."""
        return self.get_local_repository('CompanyShareOption')

    @property
    def company_share_portfolio_option_local_repo(self):
        """Get portfolio_company_share_option repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioOption')
    @property
    def company_share_portfolio_option_portfolio_local_repo(self):
        """Get portfolio_company_share_option_portfolio repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioOptionPortfolio')
    @property
    def company_share_option_price_return_factor_local_repo(self):
        """Get company_share_option_price_return_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareOptionPriceReturnFactor')

    @property
    def company_share_portfolio_option_price_return_factor_local_repo(self):
        """Get portfolio_company_share_option_price_return_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioOptionPriceReturnFactor')

    @property
    def company_share_portfolio_option_delta_factor_local_repo(self):
        """Get portfolio_company_share_option_delta_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioOptionDeltaFactor')

    @property
    def company_share_portfolio_option_price_factor_local_repo(self):
        """Get portfolio_company_share_option_price_factor repository for dependency injection."""
        return self.get_local_repository('CompanySharePortfolioOptionPriceFactor')

    # Missing IBKR properties for already registered repositories
    @property
    def company_share_factor_ibkr_repo(self):
        """Get company_share_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareFactor')

    @property
    def company_share_price_return_factor_ibkr_repo(self):
        """Get company_share_price_return_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanySharePriceReturnFactor')

    @property
    def company_share_avg_turnover_6m_factor_local_repo(self):
        """Get company_share_avg_turnover_6m_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareAvgTurnover6mFactor')

    @property
    def company_share_avg_turnover_6m_factor_ibkr_repo(self):
        """Get company_share_avg_turnover_6m_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareAvgTurnover6mFactor')

    @property
    def company_share_monthly_price_range_factor_local_repo(self):
        """Get company_share_monthly_price_range_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareMonthlyPriceRangeFactor')

    @property
    def company_share_monthly_price_range_factor_ibkr_repo(self):
        """Get company_share_monthly_price_range_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareMonthlyPriceRangeFactor')

    @property
    def company_share_vpt_52w_20d_lag_factor_local_repo(self):
        """Get company_share_vpt_52w_20d_lag_factor repository for dependency injection."""
        return self.get_local_repository('CompanyShareVpt52w20dLagFactor')

    @property
    def company_share_vpt_52w_20d_lag_factor_ibkr_repo(self):
        """Get company_share_vpt_52w_20d_lag_factor repository for dependency injection."""
        return self.get_ibkr_repository('CompanyShareVpt52w20dLagFactor')
