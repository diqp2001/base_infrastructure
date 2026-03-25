"""
Repository Factory - Centralized creation and dependency injection for repositories.

This factory manages the creation of local and IBKR repositories with proper dependency injection,
following the Domain-Driven Design principles and eliminating direct parameter passing.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Local repositories
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_price_return_factor_repository import IBKRCompanySharePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_price_return_factor_repository import CompanySharePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_factor_repository import CompanyShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_factor_repository import IBKRCompanyShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.finance.instrument_repository import IBKRInstrumentRepository
from src.infrastructure.repositories.local_repo.finance.instrument_repository import InstrumentRepository
from src.infrastructure.repositories.local_repo.geographic.sector_repository import SectorRepository
from src.infrastructure.repositories.local_repo.geographic.industry_repository import IndustryRepository
from src.infrastructure.repositories.local_repo.finance.position_repository import PositionRepository
from src.infrastructure.repositories.local_repo.finance.portfolio_repository import PortfolioRepository
from src.infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
from src.infrastructure.repositories.local_repo.finance.holding.holding_repository import HoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.portfolio_holding_repository import PortfolioHoldingRepository
from src.infrastructure.repositories.local_repo.finance.holding.portfolio_company_share_holding_repository import PortfolioCompanyShareHoldingRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.financial_statement_repository import FinancialStatementRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.income_statement_repository import IncomeStatementRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.balance_sheet_repository import BalanceSheetRepository
from src.infrastructure.repositories.local_repo.finance.financial_statements.cash_flow_statement_repository import CashFlowStatementRepository
from src.infrastructure.repositories.local_repo.finance.market_data_repository import MarketDataRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_instrument_factor_repository import IBKRInstrumentFactorRepository
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_repository import FactorRepository
from src.infrastructure.repositories.local_repo.factor.factor_value_repository import FactorValueRepository
from src.infrastructure.repositories.local_repo.factor.factor_dependency_repository import FactorDependencyRepository

# Local Factor repositories
from src.infrastructure.repositories.local_repo.factor.continent_factor_repository import ContinentFactorRepository
from src.infrastructure.repositories.local_repo.factor.country_factor_repository import CountryFactorRepository

# New Local Factor repositories
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_factor_repository import PortfolioFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_correlation_factor_repository import PortfolioCompanyShareCorrelationFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_return_factor_repository import PortfolioCompanyShareReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_value_factor_repository import PortfolioCompanyShareValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_variance_factor_repository import PortfolioCompanyShareVarianceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.holding_factor_repository import HoldingFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_holding_factor_repository import PortfolioCompanyShareHoldingFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_holding_quantity_factor_repository import PortfolioCompanyShareHoldingQuantityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_holding_value_factor_repository import PortfolioCompanyShareHoldingValueFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_company_share_holding_weight_factor_repository import PortfolioCompanyShareHoldingWeightFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.portfolio_holding_factor_repository import PortfolioHoldingFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_gamma_factor_repository import CompanyShareOptionGammaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_rho_factor_repository import CompanyShareOptionRhoFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_vega_factor_repository import CompanyShareOptionVegaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_factor_repository import IndexFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_price_return_factor_repository import IndexPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.future_price_return_factor_repository import FuturePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_price_return_factor_repository import IndexFuturePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.equity_factor_repository import EquityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.bond_factor_repository import BondFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.derivative_factor_repository import DerivativeFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.financial_asset_factor_repository import FinancialAssetFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.security_factor_repository import SecurityFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.futures_factor_repository import FuturesFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_factor_repository import IndexFutureFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_option_factor_repository import IndexFutureOptionFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_option_price_return_factor_repository import IndexFutureOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_option_price_factor_repository import IndexFutureOptionPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index_future_option_delta_factor_repository import IndexFutureOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.options_factor_repository import OptionsFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_price_return_factor_repository import CompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.portfolio_company_share_option_price_return_factor_repository import PortfolioCompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.portfolio_company_share_option_delta_factor_repository import PortfolioCompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.portfolio_company_share_option_price_factor_repository import PortfolioCompanyShareOptionPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.portfolio_company_share_option_factor_repository import PortfolioCompanyShareOptionFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.etf_share_portfolio_company_share_option_delta_factor_repository import ETFSharePortfolioCompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.etf_share_portfolio_company_share_option_factor_repository import ETFSharePortfolioCompanyShareOptionFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.etf_share_portfolio_company_share_option_price_factor_repository import ETFSharePortfolioCompanyShareOptionPriceFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.etf_share_portfolio_company_share_option_price_return_factor_repository import ETFSharePortfolioCompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.etf_share_portfolio_company_share_factor_repository import ETFSharePortfolioCompanyShareFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.etf_share_portfolio_company_share_price_return_factor_repository import ETFSharePortfolioCompanySharePriceReturnFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_delta_factor_repository import CompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_factor_repository import CompanyShareOptionFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_option_price_factor_repository import CompanyShareOptionPriceFactorRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.portfolio_company_share_option_repository import PortfolioCompanyShareOptionRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.cash_repository import CashRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.commodity_repository import CommodityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.crypto_repository import CryptoRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.equity_repository import EquityRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.etf_share_repository import ETFShareRepository
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
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_portfolio_company_share_option_factor_repository import IBKRPortfolioCompanyShareOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_etf_share_portfolio_company_share_option_delta_factor_repository import IBKRETFSharePortfolioCompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_etf_share_portfolio_company_share_option_factor_repository import IBKRETFSharePortfolioCompanyShareOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_etf_share_portfolio_company_share_option_price_factor_repository import IBKRETFSharePortfolioCompanyShareOptionPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_etf_share_portfolio_company_share_option_price_return_factor_repository import IBKRETFSharePortfolioCompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_etf_share_portfolio_company_share_factor_repository import IBKRETFSharePortfolioCompanyShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_etf_share_portfolio_company_share_price_return_factor_repository import IBKRETFSharePortfolioCompanySharePriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_delta_factor_repository import IBKRCompanyShareOptionDeltaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_factor_repository import IBKRCompanyShareOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_gamma_factor_repository import IBKRCompanyShareOptionGammaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_price_factor_repository import IBKRCompanyShareOptionPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_price_return_factor_repository import IBKRCompanyShareOptionPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_rho_factor_repository import IBKRCompanyShareOptionRhoFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_company_share_option_vega_factor_repository import IBKRCompanyShareOptionVegaFactorRepository

# IBKR Factor repositories
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_continent_factor_repository import IBKRContinentFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_country_factor_repository import IBKRCountryFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_factor_repository import IBKRIndexFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_price_return_factor_repository import IBKRIndexPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_price_return_factor_repository import IBKRIndexFuturePriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_share_factor_repository import IBKRShareFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_currency_factor_repository import IBKRCurrencyFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_equity_factor_repository import IBKREquityFactorRepository

# New IBKR Factor repositories
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_portfolio_factor_repository import IBKRPortfolioFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_portfolio_company_share_correlation_factor_repository import IBKRPortfolioCompanyShareCorrelationFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_bond_factor_repository import IBKRBondFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_derivative_factor_repository import IBKRDerivativeFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_future_factor_repository import IBKRFutureFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_factor_repository import IBKRIndexFutureFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_option_factor_repository import IBKRIndexFutureOptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_option_price_return_factor_repository import IBKRIndexFutureOptionPriceReturnFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_option_price_factor_repository import IBKRIndexFutureOptionPriceFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_future_option_delta_factor_repository import IBKRIndexFutureOptionDeltaFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_option_factor_repository import IBKROptionFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_financial_asset_factor_repository import IBKRFinancialAssetFactorRepository
from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_security_factor_repository import IBKRSecurityFactorRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.bond_repository import IBKRBondRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.cash_repository import IBKRCashRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.commodity_repository import IBKRCommodityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.company_share_repository import IBKRCompanyShareRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.crypto_repository import IBKRCryptoRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.currency_repository import IBKRCurrencyRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.equity_repository import IBKREquityRepository
from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.etf_share_repository import IBKRETFShareRepository
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
                'instrument': InstrumentRepository(self.session, factory=self),
                'factor_value': FactorValueRepository(self.session, factory=self),
                'factor': FactorRepository(self.session, factory=self),
                'factor_dependency': FactorDependencyRepository(self.session),
                'financial_asset': FinancialAssetRepository(self.session, factory=self),
                # Individual factor repositories
                'continent_factor': ContinentFactorRepository(self.session, factory=self),
                'country_factor': CountryFactorRepository(self.session, factory=self),
                'index_factor': IndexFactorRepository(self.session, factory=self),
                'index_price_return_factor': IndexPriceReturnFactorRepository(self.session, factory=self),
                'future_price_return_factor': FuturePriceReturnFactorRepository(self.session, factory=self),
                'index_future_price_return_factor': IndexFuturePriceReturnFactorRepository(self.session, factory=self),
                'share_factor': ShareFactorRepository(self.session, factory=self),
                'currency_factor': CurrencyFactorRepository(self.session, factory=self),
                'equity_factor': EquityFactorRepository(self.session, factory=self),
                'bond_factor': BondFactorRepository(self.session, factory=self),
                'derivative_factor': DerivativeFactorRepository(self.session, factory=self),
                'financial_asset_factor': FinancialAssetFactorRepository(self.session, factory=self),
                'security_factor': SecurityFactorRepository(self.session, factory=self),
                'future_factor': FuturesFactorRepository(self.session, factory=self),
                'index_future_factor': IndexFutureFactorRepository(self.session, factory=self),
                'index_future_option_factor': IndexFutureOptionFactorRepository(self.session, factory=self),
                'index_future_option_price_return_factor': IndexFutureOptionPriceReturnFactorRepository(self.session, factory=self),
                'index_future_option_price_factor': IndexFutureOptionPriceFactorRepository(self.session, factory=self),
                'index_future_option_delta_factor': IndexFutureOptionDeltaFactorRepository(self.session, factory=self),
                'option_factor': OptionsFactorRepository(self.session, factory=self),
                'company_share_option_price_return_factor': CompanyShareOptionPriceReturnFactorRepository(self.session, factory=self),
                'portfolio_company_share_option_price_return_factor': PortfolioCompanyShareOptionPriceReturnFactorRepository(self.session, factory=self),
                'portfolio_company_share_option_delta_factor': PortfolioCompanyShareOptionDeltaFactorRepository(self.session, factory=self),
                'portfolio_company_share_option_price_factor': PortfolioCompanyShareOptionPriceFactorRepository(self.session, factory=self),
                'portfolio_company_share_option_factor': PortfolioCompanyShareOptionFactorRepository(self.session, factory=self),
                'etf_share_portfolio_company_share_option_delta_factor': ETFSharePortfolioCompanyShareOptionDeltaFactorRepository(self.session, factory=self),
                'etf_share_portfolio_company_share_option_factor': ETFSharePortfolioCompanyShareOptionFactorRepository(self.session, factory=self),
                'etf_share_portfolio_company_share_option_price_factor': ETFSharePortfolioCompanyShareOptionPriceFactorRepository(self.session, factory=self),
                'etf_share_portfolio_company_share_option_price_return_factor': ETFSharePortfolioCompanyShareOptionPriceReturnFactorRepository(self.session, factory=self),
                'etf_share_portfolio_company_share_factor': ETFSharePortfolioCompanyShareFactorRepository(self.session, factory=self),
                'etf_share_portfolio_company_share_price_return_factor': ETFSharePortfolioCompanySharePriceReturnFactorRepository(self.session, factory=self),
                'company_share_option_delta_factor': CompanyShareOptionDeltaFactorRepository(self.session, factory=self),
                'company_share_option_factor': CompanyShareOptionFactorRepository(self.session, factory=self),
                'company_share_option_price_factor': CompanyShareOptionPriceFactorRepository(self.session, factory=self),
                # New factor repositories
                'portfolio_factor': PortfolioFactorRepository(self.session, factory=self),
                'portfolio_company_share_correlation_factor': PortfolioCompanyShareCorrelationFactorRepository(self.session, factory=self),
                'portfolio_company_share_return_factor': PortfolioCompanyShareReturnFactorRepository(self.session, factory=self),
                'portfolio_company_share_value_factor': PortfolioCompanyShareValueFactorRepository(self.session, factory=self),
                'portfolio_company_share_variance_factor': PortfolioCompanyShareVarianceFactorRepository(self.session, factory=self),
                'holding_factor': HoldingFactorRepository(self.session, factory=self),
                'portfolio_company_share_holding_factor': PortfolioCompanyShareHoldingFactorRepository(self.session, factory=self),
                'portfolio_company_share_holding_quantity_factor': PortfolioCompanyShareHoldingQuantityFactorRepository(self.session, factory=self),
                'portfolio_company_share_holding_value_factor': PortfolioCompanyShareHoldingValueFactorRepository(self.session, factory=self),
                'portfolio_company_share_holding_weight_factor': PortfolioCompanyShareHoldingWeightFactorRepository(self.session, factory=self),
                'portfolio_holding_factor': PortfolioHoldingFactorRepository(self.session, factory=self),
                'company_share_option_gamma_factor': CompanyShareOptionGammaFactorRepository(self.session, factory=self),
                'company_share_option_rho_factor': CompanyShareOptionRhoFactorRepository(self.session, factory=self),
                'company_share_option_vega_factor': CompanyShareOptionVegaFactorRepository(self.session, factory=self),
                'index_future': IndexFutureRepository(self.session, factory=self),
                'index_future_option': IndexFutureOptionRepository(self.session, factory=self),
                'company_share_option': CompanyShareOptionRepository(self.session, factory=self),
                'portfolio_company_share_option': PortfolioCompanyShareOptionRepository(self.session, factory=self),
                'company_share': CompanyShareRepository(self.session, factory=self),
                'company_share_factor': CompanyShareFactorRepository(self.session, factory=self),
                'company_share_price_return_factor': CompanySharePriceReturnFactorRepository(self.session, factory=self),
                'currency': CurrencyRepository(self.session, factory=self),
                'bond': BondRepository(self.session, factory=self),
                'index': IndexRepository(self.session, factory=self),
                'crypto': CryptoRepository(self.session, factory=self),
                'commodity': CommodityRepository(self.session, factory=self),  
                'cash': CashRepository(self.session, factory=self),
                'equity': EquityRepository(self.session, factory=self),
                'etf_share': ETFShareRepository(self.session, factory=self),  
                'share': ShareRepository(self.session, factory=self),
                'security': SecurityRepository(self.session, factory=self),
                'country': CountryRepository(self.session, factory=self),
                'continent': ContinentRepository(self.session, factory=self),
                'exchange': ExchangeRepository(self.session, factory=self),
                # Additional geographic repositories
                'sector': SectorRepository(self.session, factory=self),
                'industry': IndustryRepository(self.session, factory=self),
                # Portfolio and position repositories
                'position': PositionRepository(self.session, factory=self),
                'portfolio': PortfolioRepository(self.session, factory=self),
                'company': CompanyRepository(self.session, factory=self),
                # Holding repositories
                'holding': HoldingRepository(self.session, factory=self),
                'portfolio_holding': PortfolioHoldingRepository(self.session, factory=self),
                'portfolio_company_share_holding': PortfolioCompanyShareHoldingRepository(self.session, factory=self),
                # Financial statement repositories
                'financial_statement': FinancialStatementRepository(self.session, factory=self),
                'income_statement': IncomeStatementRepository(self.session, factory=self),
                'balance_sheet': BalanceSheetRepository(self.session, factory=self),
                'cash_flow_statement': CashFlowStatementRepository(self.session, factory=self),
                # Market data repository
                'market_data': MarketDataRepository(self.session, factory=self)
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
            # Ensure local repositories exist first
            
            self._ibkr_repositories = {
                'instrument_factor': IBKRInstrumentFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'instrument': IBKRInstrumentRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'factor': IBKRFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'factor_value': IBKRFactorValueRepository(
                    ibkr_client=client,
                    factory=self
                ),
                # Individual factor repositories
                'continent_factor': IBKRContinentFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'country_factor': IBKRCountryFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_factor': IBKRIndexFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_price_return_factor': IBKRIndexPriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_price_return_factor': IBKRIndexFuturePriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'share_factor': IBKRShareFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_factor': IBKRCompanyShareFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_price_return_factor': IBKRCompanySharePriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'portfolio_company_share_option_factor': IBKRPortfolioCompanyShareOptionFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share_portfolio_company_share_option_delta_factor': IBKRETFSharePortfolioCompanyShareOptionDeltaFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share_portfolio_company_share_option_factor': IBKRETFSharePortfolioCompanyShareOptionFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share_portfolio_company_share_option_price_factor': IBKRETFSharePortfolioCompanyShareOptionPriceFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share_portfolio_company_share_option_price_return_factor': IBKRETFSharePortfolioCompanyShareOptionPriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share_portfolio_company_share_factor': IBKRETFSharePortfolioCompanyShareFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share_portfolio_company_share_price_return_factor': IBKRETFSharePortfolioCompanySharePriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_delta_factor': IBKRCompanyShareOptionDeltaFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_factor': IBKRCompanyShareOptionFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_gamma_factor': IBKRCompanyShareOptionGammaFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_price_factor': IBKRCompanyShareOptionPriceFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_price_return_factor': IBKRCompanyShareOptionPriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_rho_factor': IBKRCompanyShareOptionRhoFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option_vega_factor': IBKRCompanyShareOptionVegaFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'currency_factor': IBKRCurrencyFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'equity_factor': IBKREquityFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                # New IBKR factor repositories
                'bond_factor': IBKRBondFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'derivative_factor': IBKRDerivativeFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'future_factor': IBKRFutureFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_factor': IBKRIndexFutureFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_option_factor': IBKRIndexFutureOptionFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_option_price_return_factor': IBKRIndexFutureOptionPriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_option_price_factor': IBKRIndexFutureOptionPriceFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_option_delta_factor': IBKRIndexFutureOptionDeltaFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'option_factor': IBKROptionFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'financial_asset_factor': IBKRFinancialAssetFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'security_factor': IBKRSecurityFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                # New IBKR factor repositories
                'portfolio_factor': IBKRPortfolioFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'portfolio_company_share_correlation_factor': IBKRPortfolioCompanyShareCorrelationFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future': IBKRIndexFutureRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index_future_option': IBKRIndexFutureOptionRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company_share_option': IBKRCompanyShareOptionRepository(
                    ibkr_client=client,
                    factory=self
                ),
                
                'company_share': IBKRCompanyShareRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'currency': IBKRCurrencyRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'bond': IBKRBondRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'index': IBKRIndexRepository(
                    ibkr_client=client,
                    factory=self  
                ),
                'crypto': IBKRCryptoRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'commodity': IBKRCommodityRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'cash': IBKRCashRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'equity': IBKREquityRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'etf_share': IBKRETFShareRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'share': IBKRShareRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'security': IBKRSecurityRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'country': IBKRCountryRepository(ibkr_client=client,
                    factory=self),
                'continent': IBKRContinentRepository(ibkr_client=client,
                    factory=self),
                'exchange': IBKRExchangeRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'company': IBKRCompanyRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'industry': IBKRIndustryRepository(
                    ibkr_client=client,
                    factory=self
                ),
                'sector': IBKRSectorRepository(
                    ibkr_client=client,
                    factory=self
                )
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
                'enable_logging': True
            }
            
            client = create_interactive_brokers_broker(**ib_config)
            client.connect()
            
            self.ibkr_client = client
            return client
            
        except Exception as e:
            print(f"Error creating IBKR client: {e}")
            return None

    def get_local_repository(self, entity_class: type):
        """
        Get local repository for a given entity class.
        
        Args:
            entity_class: Domain entity class
            
        Returns:
            Repository instance or None if not found
        """
        repos = self.create_local_repositories()
        for repo in repos.values():
            if hasattr(repo, 'entity_class') and repo.entity_class is entity_class:
                return repo
        return None

    def get_ibkr_repository(self, entity_class: type):
        """
        Get IBKR repository for a given entity class.
        
        Args:
            entity_class: Domain entity class
            
        Returns:
            Repository instance or None if not found or no IBKR client
        """
        repos = self.create_ibkr_repositories()
        if not repos:
            return None
            
        for repo in repos.values():
            if hasattr(repo, 'entity_class') and repo.entity_class is entity_class:
                return repo
        return None

    def has_ibkr_client(self) -> bool:
        """Check if IBKR client is available."""
        return self.ibkr_client is not None
    
    @property
    def instrument_local_repo(self):
        """Get instrument repository for dependency injection."""
        return self._local_repositories.get('instrument')
    
    @property
    def financial_asset_local_repo(self):
        """Get financial_asset repository for dependency injection."""
        return self._local_repositories.get('financial_asset')
    
    @property
    def factor_value_local_repo(self):
        """Get factor_value repository for dependency injection."""
        return self._local_repositories.get('factor_value')


    @property
    def factor_local_repo(self):
        """Get factor repository for dependency injection."""
        return self._local_repositories.get('factor')

    @property
    def factor_dependency_local_repo(self):
        """Get factor_dependency repository for dependency injection."""
        return self._local_repositories.get('factor_dependency')

    # Individual local factor repositories
    @property
    def continent_factor_local_repo(self):
        """Get continent_factor repository for dependency injection."""
        return self._local_repositories.get('continent_factor')

    @property
    def country_factor_local_repo(self):
        """Get country_factor repository for dependency injection."""
        return self._local_repositories.get('country_factor')

    @property
    def index_factor_local_repo(self):
        """Get index_factor repository for dependency injection."""
        return self._local_repositories.get('index_factor')

    @property
    def index_price_return_factor_local_repo(self):
        """Get index_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('index_price_return_factor')

    @property
    def currency_factor_local_repo(self):
        """Get currency_factor repository for dependency injection."""
        return self._local_repositories.get('currency_factor')

    @property
    def equity_factor_local_repo(self):
        """Get equity_factor repository for dependency injection."""
        return self._local_repositories.get('equity_factor')

    @property
    def bond_factor_local_repo(self):
        """Get bond_factor repository for dependency injection."""
        return self._local_repositories.get('bond_factor')

    @property
    def derivative_factor_local_repo(self):
        """Get derivative_factor repository for dependency injection."""
        return self._local_repositories.get('derivative_factor')

    @property
    def financial_asset_factor_local_repo(self):
        """Get financial_asset_factor repository for dependency injection."""
        return self._local_repositories.get('financial_asset_factor')

    @property
    def security_factor_local_repo(self):
        """Get security_factor repository for dependency injection."""
        return self._local_repositories.get('security_factor')

    @property
    def future_factor_local_repo(self):
        """Get future_factor repository for dependency injection."""
        return self._local_repositories.get('future_factor')

    @property
    def index_future_factor_local_repo(self):
        """Get index_future_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_factor')

    @property
    def option_factor_local_repo(self):
        """Get option_factor repository for dependency injection."""
        return self._local_repositories.get('option_factor')


    @property
    def base_factor_local_repo(self):
        """Get base_factor repository for dependency injection."""
        return self._local_repositories.get('base_factor')


    @property
    def share_factor_local_repo(self):
        """Get share_factor repository for dependency injection."""
        return self._local_repositories.get('share_factor')


    @property
    def index_future_local_repo(self):
        """Get index_future repository for dependency injection."""
        return self._local_repositories.get('index_future')

    @property
    def index_future_option_local_repo(self):
        """Get index_future_option repository for dependency injection."""
        return self._local_repositories.get('index_future_option')

    @property
    def index_future_option_factor_local_repo(self):
        """Get index_future_option_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_option_factor')

    @property
    def index_future_option_price_return_factor_local_repo(self):
        """Get index_future_option_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_option_price_return_factor')

    @property
    def index_future_option_price_factor_local_repo(self):
        """Get index_future_option_price_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_option_price_factor')

    @property
    def index_future_option_delta_factor_local_repo(self):
        """Get index_future_option_delta_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_option_delta_factor')

    @property
    def company_share_local_repo(self):
        """Get company_share repository for dependency injection."""
        return self._local_repositories.get('company_share')


    @property
    def currency_local_repo(self):
        """Get currency repository for dependency injection."""
        return self._local_repositories.get('currency')


    @property
    def bond_local_repo(self):
        """Get bond repository for dependency injection."""
        return self._local_repositories.get('bond')


    @property
    def index_local_repo(self):
        """Get index repository for dependency injection."""
        return self._local_repositories.get('index')


    @property
    def crypto_local_repo(self):
        """Get crypto repository for dependency injection."""
        return self._local_repositories.get('crypto')


    @property
    def commodity_local_repo(self):
        """Get commodity repository for dependency injection."""
        return self._local_repositories.get('commodity')


    @property
    def cash_local_repo(self):
        """Get cash repository for dependency injection."""
        return self._local_repositories.get('cash')


    @property
    def equity_local_repo(self):
        """Get equity repository for dependency injection."""
        return self._local_repositories.get('equity')


    @property
    def etf_share_local_repo(self):
        """Get etf_share repository for dependency injection."""
        return self._local_repositories.get('etf_share')


    @property
    def share_local_repo(self):
        """Get share repository for dependency injection."""
        return self._local_repositories.get('share')


    @property
    def security_local_repo(self):
        """Get security repository for dependency injection."""
        return self._local_repositories.get('security')

    @property
    def country_local_repo(self):
        """Get country repository for dependency injection."""
        return self._local_repositories.get('country')

    @property
    def continent_local_repo(self):
        """Get continent repository for dependency injection."""
        return self._local_repositories.get('continent')

    @property
    def exchange_local_repo(self):
        """Get exchange repository for dependency injection."""
        return self._local_repositories.get('exchange')

    @property
    def instrument_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self._ibkr_repositories.get('instrument')
    @property
    def instrument_factor_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self._ibkr_repositories.get('instrument_factor')
    @property
    def factor_ibkr_repo(self):
        """Get factor repository for dependency injection."""
        return self._ibkr_repositories.get('factor')


    @property
    def factor_value_ibkr_repo(self):
        """Get factor_value repository for dependency injection."""
        return self._ibkr_repositories.get('factor_value')

    # Individual IBKR factor repositories
    @property
    def continent_factor_ibkr_repo(self):
        """Get continent_factor repository for dependency injection."""
        return self._ibkr_repositories.get('continent_factor')

    @property
    def country_factor_ibkr_repo(self):
        """Get country_factor repository for dependency injection."""
        return self._ibkr_repositories.get('country_factor')

    @property
    def index_factor_ibkr_repo(self):
        """Get index_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_factor')

    @property
    def index_price_return_factor_ibkr_repo(self):
        """Get index_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_price_return_factor')

    @property
    def index_future_price_return_factor_ibkr_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_price_return_factor')

    @property
    def share_factor_ibkr_repo(self):
        """Get share_factor repository for dependency injection."""
        return self._ibkr_repositories.get('share_factor')

    @property
    def currency_factor_ibkr_repo(self):
        """Get currency_factor repository for dependency injection."""
        return self._ibkr_repositories.get('currency_factor')

    @property
    def equity_factor_ibkr_repo(self):
        """Get equity_factor repository for dependency injection."""
        return self._ibkr_repositories.get('equity_factor')


    @property
    def index_future_ibkr_repo(self):
        """Get index_future repository for dependency injection."""
        return self._ibkr_repositories.get('index_future')

    @property
    def index_future_option_ibkr_repo(self):
        """Get index_future_option repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_option')

    @property
    def index_future_option_factor_ibkr_repo(self):
        """Get index_future_option_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_option_factor')

    @property
    def index_future_option_price_return_factor_ibkr_repo(self):
        """Get index_future_option_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_option_price_return_factor')

    @property
    def index_future_option_price_factor_ibkr_repo(self):
        """Get index_future_option_price_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_option_price_factor')

    @property
    def index_future_option_delta_factor_ibkr_repo(self):
        """Get index_future_option_delta_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_option_delta_factor')

    @property
    def company_share_ibkr_repo(self):
        """Get company_share repository for dependency injection."""
        return self._ibkr_repositories.get('company_share')


    @property
    def currency_ibkr_repo(self):
        """Get currency repository for dependency injection."""
        return self._ibkr_repositories.get('currency')


    @property
    def bond_ibkr_repo(self):
        """Get bond repository for dependency injection."""
        return self._ibkr_repositories.get('bond')


    @property
    def index_ibkr_repo(self):
        """Get index repository for dependency injection."""
        return self._ibkr_repositories.get('index')


    @property
    def crypto_ibkr_repo(self):
        """Get crypto repository for dependency injection."""
        return self._ibkr_repositories.get('crypto')


    @property
    def commodity_ibkr_repo(self):
        """Get commodity repository for dependency injection."""
        return self._ibkr_repositories.get('commodity')


    @property
    def cash_ibkr_repo(self):
        """Get cash repository for dependency injection."""
        return self._ibkr_repositories.get('cash')


    @property
    def equity_ibkr_repo(self):
        """Get equity repository for dependency injection."""
        return self._ibkr_repositories.get('equity')


    @property
    def etf_share_ibkr_repo(self):
        """Get etf_share repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share')


    @property
    def share_ibkr_repo(self):
        """Get share repository for dependency injection."""
        return self._ibkr_repositories.get('share')


    @property
    def security_ibkr_repo(self):
        """Get security repository for dependency injection."""
        return self._ibkr_repositories.get('security')

    @property
    def country_ibkr_repo(self):
        """Get country repository for dependency injection."""
        return self._ibkr_repositories.get('country')

    @property
    def continent_ibkr_repo(self):
        """Get continent repository for dependency injection."""
        return self._ibkr_repositories.get('continent')

    @property
    def exchange_ibkr_repo(self):
        """Get exchange repository for dependency injection."""
        return self._ibkr_repositories.get('exchange')

    # New IBKR factor repository properties
    @property
    def bond_factor_ibkr_repo(self):
        """Get bond_factor repository for dependency injection."""
        return self._ibkr_repositories.get('bond_factor')

    @property
    def derivative_factor_ibkr_repo(self):
        """Get derivative_factor repository for dependency injection."""
        return self._ibkr_repositories.get('derivative_factor')

    @property
    def future_factor_ibkr_repo(self):
        """Get future_factor repository for dependency injection."""
        return self._ibkr_repositories.get('future_factor')

    @property
    def index_future_factor_ibkr_repo(self):
        """Get index_future_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_factor')

    @property
    def option_factor_ibkr_repo(self):
        """Get option_factor repository for dependency injection."""
        return self._ibkr_repositories.get('option_factor')

    @property
    def financial_asset_factor_ibkr_repo(self):
        """Get financial_asset_factor repository for dependency injection."""
        return self._ibkr_repositories.get('financial_asset_factor')

    @property
    def security_factor_ibkr_repo(self):
        """Get security_factor repository for dependency injection."""
        return self._ibkr_repositories.get('security_factor')
    
    # Additional local repository properties
    @property
    def sector_local_repo(self):
        """Get sector repository for dependency injection."""
        return self._local_repositories.get('sector')
    
    @property
    def industry_local_repo(self):
        """Get industry repository for dependency injection."""
        return self._local_repositories.get('industry')
    
    @property
    def position_local_repo(self):
        """Get position repository for dependency injection."""
        return self._local_repositories.get('position')
    
    @property
    def portfolio_local_repo(self):
        """Get portfolio repository for dependency injection."""
        return self._local_repositories.get('portfolio')
    
    @property
    def company_local_repo(self):
        """Get company repository for dependency injection."""
        return self._local_repositories.get('company')
    
    @property
    def holding_local_repo(self):
        """Get holding repository for dependency injection."""
        return self._local_repositories.get('holding')
    
    @property
    def portfolio_holding_local_repo(self):
        """Get portfolio_holding repository for dependency injection."""
        return self._local_repositories.get('portfolio_holding')
    
    @property
    def portfolio_company_share_holding_local_repo(self):
        """Get portfolio_company_share_holding repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_holding')
    
    @property
    def financial_statement_local_repo(self):
        """Get financial_statement repository for dependency injection."""
        return self._local_repositories.get('financial_statement')
    
    @property
    def income_statement_local_repo(self):
        """Get income_statement repository for dependency injection."""
        return self._local_repositories.get('income_statement')
    
    @property
    def balance_sheet_local_repo(self):
        """Get balance_sheet repository for dependency injection."""
        return self._local_repositories.get('balance_sheet')
    
    @property
    def cash_flow_statement_local_repo(self):
        """Get cash_flow_statement repository for dependency injection."""
        return self._local_repositories.get('cash_flow_statement')
    
    @property
    def market_data_local_repo(self):
        """Get market_data repository for dependency injection."""
        return self._local_repositories.get('market_data')
    
    @property
    def future_price_return_factor_local_repo(self):
        """Get future_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('future_price_return_factor')
    
    @property
    def index_future_price_return_factor_local_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_price_return_factor')
    
    # Additional IBKR repository properties
    @property
    def company_ibkr_repo(self):
        """Get company repository for dependency injection."""
        return self._ibkr_repositories.get('company')

    @property
    def industry_ibkr_repo(self):
        """Get industry repository for dependency injection."""
        return self._ibkr_repositories.get('industry')

    @property
    def sector_ibkr_repo(self):
        """Get sector repository for dependency injection."""
        return self._ibkr_repositories.get('sector')

    # New local repository properties
    @property
    def portfolio_factor_local_repo(self):
        """Get portfolio_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_factor')
    
    @property
    def portfolio_company_share_correlation_factor_local_repo(self):
        """Get portfolio_company_share_correlation_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_correlation_factor')
    
    @property
    def portfolio_company_share_return_factor_local_repo(self):
        """Get portfolio_company_share_return_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_return_factor')
    
    @property
    def portfolio_company_share_value_factor_local_repo(self):
        """Get portfolio_company_share_value_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_value_factor')
    
    @property
    def portfolio_company_share_variance_factor_local_repo(self):
        """Get portfolio_company_share_variance_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_variance_factor')
    
    @property
    def holding_factor_local_repo(self):
        """Get holding_factor repository for dependency injection."""
        return self._local_repositories.get('holding_factor')
    
    @property
    def portfolio_company_share_holding_factor_local_repo(self):
        """Get portfolio_company_share_holding_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_holding_factor')
    
    @property
    def portfolio_company_share_holding_quantity_factor_local_repo(self):
        """Get portfolio_company_share_holding_quantity_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_holding_quantity_factor')
    
    @property
    def portfolio_company_share_holding_value_factor_local_repo(self):
        """Get portfolio_company_share_holding_value_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_holding_value_factor')
    
    @property
    def portfolio_company_share_holding_weight_factor_local_repo(self):
        """Get portfolio_company_share_holding_weight_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_holding_weight_factor')
    
    @property
    def portfolio_holding_factor_local_repo(self):
        """Get portfolio_holding_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_holding_factor')
    
    @property
    def company_share_option_gamma_factor_local_repo(self):
        """Get company_share_option_gamma_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_gamma_factor')
    
    @property
    def company_share_option_rho_factor_local_repo(self):
        """Get company_share_option_rho_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_rho_factor')
    
    @property
    def company_share_option_vega_factor_local_repo(self):
        """Get company_share_option_vega_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_vega_factor')

    # New IBKR repository properties
    @property
    def portfolio_factor_ibkr_repo(self):
        """Get portfolio_factor repository for dependency injection."""
        return self._ibkr_repositories.get('portfolio_factor')
    
    @property
    def portfolio_company_share_correlation_factor_ibkr_repo(self):
        """Get portfolio_company_share_correlation_factor repository for dependency injection."""
        return self._ibkr_repositories.get('portfolio_company_share_correlation_factor')

    # New Local repository properties
    @property
    def portfolio_company_share_option_factor_local_repo(self):
        """Get portfolio_company_share_option_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_option_factor')

    @property
    def etf_share_portfolio_company_share_option_delta_factor_local_repo(self):
        """Get etf_share_portfolio_company_share_option_delta_factor repository for dependency injection."""
        return self._local_repositories.get('etf_share_portfolio_company_share_option_delta_factor')

    @property
    def etf_share_portfolio_company_share_option_factor_local_repo(self):
        """Get etf_share_portfolio_company_share_option_factor repository for dependency injection."""
        return self._local_repositories.get('etf_share_portfolio_company_share_option_factor')

    @property
    def etf_share_portfolio_company_share_option_price_factor_local_repo(self):
        """Get etf_share_portfolio_company_share_option_price_factor repository for dependency injection."""
        return self._local_repositories.get('etf_share_portfolio_company_share_option_price_factor')

    @property
    def etf_share_portfolio_company_share_option_price_return_factor_local_repo(self):
        """Get etf_share_portfolio_company_share_option_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('etf_share_portfolio_company_share_option_price_return_factor')

    @property
    def etf_share_portfolio_company_share_factor_local_repo(self):
        """Get etf_share_portfolio_company_share_factor repository for dependency injection."""
        return self._local_repositories.get('etf_share_portfolio_company_share_factor')

    @property
    def etf_share_portfolio_company_share_price_return_factor_local_repo(self):
        """Get etf_share_portfolio_company_share_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('etf_share_portfolio_company_share_price_return_factor')

    @property
    def company_share_option_delta_factor_local_repo(self):
        """Get company_share_option_delta_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_delta_factor')

    @property
    def company_share_option_factor_local_repo(self):
        """Get company_share_option_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_factor')

    @property
    def company_share_option_price_factor_local_repo(self):
        """Get company_share_option_price_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_price_factor')

    # New IBKR repository properties
    @property
    def portfolio_company_share_option_factor_ibkr_repo(self):
        """Get portfolio_company_share_option_factor repository for dependency injection."""
        return self._ibkr_repositories.get('portfolio_company_share_option_factor')

    @property
    def etf_share_portfolio_company_share_option_delta_factor_ibkr_repo(self):
        """Get etf_share_portfolio_company_share_option_delta_factor repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share_portfolio_company_share_option_delta_factor')

    @property
    def etf_share_portfolio_company_share_option_factor_ibkr_repo(self):
        """Get etf_share_portfolio_company_share_option_factor repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share_portfolio_company_share_option_factor')

    @property
    def etf_share_portfolio_company_share_option_price_factor_ibkr_repo(self):
        """Get etf_share_portfolio_company_share_option_price_factor repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share_portfolio_company_share_option_price_factor')

    @property
    def etf_share_portfolio_company_share_option_price_return_factor_ibkr_repo(self):
        """Get etf_share_portfolio_company_share_option_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share_portfolio_company_share_option_price_return_factor')

    @property
    def etf_share_portfolio_company_share_factor_ibkr_repo(self):
        """Get etf_share_portfolio_company_share_factor repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share_portfolio_company_share_factor')

    @property
    def etf_share_portfolio_company_share_price_return_factor_ibkr_repo(self):
        """Get etf_share_portfolio_company_share_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('etf_share_portfolio_company_share_price_return_factor')

    @property
    def company_share_option_delta_factor_ibkr_repo(self):
        """Get company_share_option_delta_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_delta_factor')

    @property
    def company_share_option_factor_ibkr_repo(self):
        """Get company_share_option_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_factor')

    @property
    def company_share_option_gamma_factor_ibkr_repo(self):
        """Get company_share_option_gamma_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_gamma_factor')

    @property
    def company_share_option_price_factor_ibkr_repo(self):
        """Get company_share_option_price_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_price_factor')

    @property
    def company_share_option_price_return_factor_ibkr_repo(self):
        """Get company_share_option_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_price_return_factor')

    @property
    def company_share_option_rho_factor_ibkr_repo(self):
        """Get company_share_option_rho_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_rho_factor')

    @property
    def company_share_option_vega_factor_ibkr_repo(self):
        """Get company_share_option_vega_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_option_vega_factor')

    # Missing properties for already registered repositories
    @property
    def company_share_factor_local_repo(self):
        """Get company_share_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_factor')

    @property
    def company_share_price_return_factor_local_repo(self):
        """Get company_share_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_price_return_factor')

    @property
    def company_share_option_local_repo(self):
        """Get company_share_option repository for dependency injection."""
        return self._local_repositories.get('company_share_option')

    @property
    def portfolio_company_share_option_local_repo(self):
        """Get portfolio_company_share_option repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_option')

    @property
    def company_share_option_price_return_factor_local_repo(self):
        """Get company_share_option_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('company_share_option_price_return_factor')

    @property
    def portfolio_company_share_option_price_return_factor_local_repo(self):
        """Get portfolio_company_share_option_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_option_price_return_factor')

    @property
    def portfolio_company_share_option_delta_factor_local_repo(self):
        """Get portfolio_company_share_option_delta_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_option_delta_factor')

    @property
    def portfolio_company_share_option_price_factor_local_repo(self):
        """Get portfolio_company_share_option_price_factor repository for dependency injection."""
        return self._local_repositories.get('portfolio_company_share_option_price_factor')

    # Missing IBKR properties for already registered repositories
    @property
    def company_share_factor_ibkr_repo(self):
        """Get company_share_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_factor')

    @property
    def company_share_price_return_factor_ibkr_repo(self):
        """Get company_share_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('company_share_price_return_factor')
