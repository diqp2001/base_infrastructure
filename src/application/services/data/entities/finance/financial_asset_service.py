"""
Financial Asset Service - handles creation and management of financial asset entities.
Provides a service layer for creating financial asset domain entities like Company, CompanyShare, Currency, etc.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities.finance.company import Company
from src.domain.entities.finance.exchange import Exchange
from src.domain.entities.finance.financial_assets.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.financial_assets.crypto import Crypto
from src.domain.entities.finance.financial_assets.commodity import Commodity
from src.domain.entities.finance.financial_assets.cash import Cash
from src.domain.entities.finance.financial_assets.bond import Bond
from src.domain.entities.finance.financial_assets.index import Index
from src.domain.entities.finance.financial_assets.etf_share import ETFShare
from src.domain.entities.finance.financial_assets.security import Security
from src.domain.entities.finance.financial_assets.share import Share
from domain.entities.finance.financial_assets.derivatives.future.future import Future
from domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.stock import Stock
from src.domain.entities.finance.financial_assets.equity import Equity
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from domain.entities.finance.financial_assets.derivatives.forward import Forward

# Import existing repositories
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
from application.services.database_service.database_service import DatabaseService


class FinancialAssetService:
    """Service for creating and managing financial asset domain entities."""
    
    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite'):
        """
        Initialize the service with a database service or create one if not provided.
        
        Args:
            database_service: Optional existing DatabaseService instance
            db_type: Database type to use when creating new DatabaseService (ignored if database_service provided)
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)
        self._init_repositories()
    
    # Company and Exchange entities
    def create_company(
        self,
        name: str,
        ticker: str = None,
        exchange: str = None,
        sector: str = None,
        industry: str = None,
        country: str = None,
        market_cap: Decimal = None,
        employees: int = None,
        founded_year: int = None,
        description: str = None
    ) -> Company:
        """Create a Company entity."""
        return Company(
            name=name,
            ticker=ticker,
            exchange=exchange,
            sector=sector,
            industry=industry,
            country=country,
            market_cap=market_cap,
            employees=employees,
            founded_year=founded_year,
            description=description
        )
    
    def create_exchange(
        self,
        name: str,
        code: str,
        country: str,
        currency: str = None,
        timezone: str = None,
        market_open: str = None,
        market_close: str = None,
        website: str = None
    ) -> Exchange:
        """Create an Exchange entity."""
        return Exchange(
            name=name,
            code=code,
            country=country,
            currency=currency,
            timezone=timezone,
            market_open=market_open,
            market_close=market_close,
            website=website
        )
    
    # Financial Asset entities
    def create_company_share(
        self,
        symbol: str,
        company_name: str,
        exchange: str,
        currency: str = "USD",
        share_class: str = "Common",
        isin: str = None,
        cusip: str = None,
        sector: str = None,
        industry: str = None,
        market_cap: Decimal = None,
        shares_outstanding: int = None,
        dividend_yield: float = None
    ) -> CompanyShare:
        """Create a CompanyShare entity."""
        return CompanyShare(
            symbol=symbol,
            company_name=company_name,
            exchange=exchange,
            currency=currency,
            share_class=share_class,
            isin=isin,
            cusip=cusip,
            sector=sector,
            industry=industry,
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            dividend_yield=dividend_yield
        )
    
    def create_currency(
        self,
        code: str,
        name: str,
        symbol: str = None,
        country: str = None,
        is_crypto: bool = False,
        decimals: int = 2
    ) -> Currency:
        """Create a Currency entity."""
        return Currency(
            code=code,
            name=name,
            symbol=symbol,
            country=country,
            is_crypto=is_crypto,
            decimals=decimals
        )
    
    def create_crypto(
        self,
        symbol: str,
        name: str,
        blockchain: str = None,
        consensus_mechanism: str = None,
        max_supply: int = None,
        circulating_supply: int = None,
        launch_date: date = None,
        website: str = None
    ) -> Crypto:
        """Create a Crypto entity."""
        return Crypto(
            symbol=symbol,
            name=name,
            blockchain=blockchain,
            consensus_mechanism=consensus_mechanism,
            max_supply=max_supply,
            circulating_supply=circulating_supply,
            launch_date=launch_date,
            website=website
        )
    
    def create_commodity(
        self,
        name: str,
        symbol: str,
        category: str = None,
        unit_of_measure: str = None,
        exchange: str = None,
        contract_size: str = None,
        tick_size: Decimal = None
    ) -> Commodity:
        """Create a Commodity entity."""
        return Commodity(
            name=name,
            symbol=symbol,
            category=category,
            unit_of_measure=unit_of_measure,
            exchange=exchange,
            contract_size=contract_size,
            tick_size=tick_size
        )
    
    def create_bond(
        self,
        isin: str,
        issuer: str,
        coupon_rate: float,
        maturity_date: date,
        face_value: Decimal = Decimal('1000'),
        currency: str = "USD",
        bond_type: str = "Corporate",
        credit_rating: str = None,
        callable: bool = False
    ) -> Bond:
        """Create a Bond entity."""
        return Bond(
            isin=isin,
            issuer=issuer,
            coupon_rate=coupon_rate,
            maturity_date=maturity_date,
            face_value=face_value,
            currency=currency,
            bond_type=bond_type,
            credit_rating=credit_rating,
            callable=callable
        )
    
    def create_etf_share(
        self,
        symbol: str,
        name: str,
        exchange: str,
        currency: str = "USD",
        expense_ratio: float = None,
        aum: Decimal = None,
        inception_date: date = None,
        index_tracked: str = None,
        dividend_yield: float = None
    ) -> ETFShare:
        """Create an ETFShare entity."""
        return ETFShare(
            symbol=symbol,
            name=name,
            exchange=exchange,
            currency=currency,
            expense_ratio=expense_ratio,
            aum=aum,
            inception_date=inception_date,
            index_tracked=index_tracked,
            dividend_yield=dividend_yield
        )
    
    def create_future(
        self,
        symbol: str,
        underlying_asset: str,
        expiry_date: date,
        contract_size: str,
        exchange: str,
        currency: str = "USD",
        tick_size: Decimal = None,
        margin_requirement: Decimal = None
    ) -> Future:
        """Create a Future entity."""
        return Future(
            symbol=symbol,
            underlying_asset=underlying_asset,
            expiry_date=expiry_date,
            contract_size=contract_size,
            exchange=exchange,
            currency=currency,
            tick_size=tick_size,
            margin_requirement=margin_requirement
        )
    
    def create_option(
        self,
        symbol: str,
        underlying_asset: str,
        strike_price: Decimal,
        expiry_date: date,
        option_type: str,  # 'call' or 'put'
        exchange: str,
        currency: str = "USD",
        contract_size: int = 100,
        american_style: bool = True
    ) -> Option:
        """Create an Option entity."""
        return Option(
            symbol=symbol,
            underlying_asset=underlying_asset,
            strike_price=strike_price,
            expiry_date=expiry_date,
            option_type=option_type,
            exchange=exchange,
            currency=currency,
            contract_size=contract_size,
            american_style=american_style
        )
    
    def create_index(
        self,
        symbol: str,
        name: str,
        currency: str = "USD",
        base_value: Decimal = Decimal('100'),
        base_date: date = None,
        methodology: str = None,
        provider: str = None,
        constituents_count: int = None
    ) -> Index:
        """Create an Index entity."""
        return Index(
            symbol=symbol,
            name=name,
            currency=currency,
            base_value=base_value,
            base_date=base_date,
            methodology=methodology,
            provider=provider,
            constituents_count=constituents_count
        )
    
    def create_financial_asset(
        self,
        name: str,
        asset_type: str,
        symbol: str = None,
        currency: str = "USD",
        exchange: str = None,
        description: str = None
    ) -> FinancialAsset:
        """Create a base FinancialAsset entity."""
        return FinancialAsset(
            name=name,
            asset_type=asset_type,
            symbol=symbol,
            currency=currency,
            exchange=exchange,
            description=description
        )
    
    # Factory methods from configuration
    def create_entity_from_config(self, entity_type: str, config: Dict[str, Any]):
        """
        Create a financial entity from configuration based on entity type.
        
        Args:
            entity_type: Type of entity ('company', 'company_share', 'currency', etc.)
            config: Configuration dictionary
            
        Returns:
            Financial entity instance
        """
        entity_type = entity_type.lower()
        
        if entity_type == 'company':
            return self.create_company_from_config(config)
        elif entity_type == 'exchange':
            return self.create_exchange_from_config(config)
        elif entity_type == 'company_share':
            return self.create_company_share_from_config(config)
        elif entity_type == 'currency':
            return self.create_currency_from_config(config)
        elif entity_type == 'crypto':
            return self.create_crypto_from_config(config)
        elif entity_type == 'commodity':
            return self.create_commodity_from_config(config)
        elif entity_type == 'bond':
            return self.create_bond_from_config(config)
        elif entity_type == 'etf_share':
            return self.create_etf_share_from_config(config)
        elif entity_type == 'future':
            return self.create_future_from_config(config)
        elif entity_type == 'option':
            return self.create_option_from_config(config)
        elif entity_type == 'index':
            return self.create_index_from_config(config)
        elif entity_type == 'financial_asset':
            return self.create_financial_asset_from_config(config)
        else:
            raise ValueError(f"Unsupported financial entity type: {entity_type}")
    
    def create_company_from_config(self, config: Dict[str, Any]) -> Company:
        """Create a Company from configuration."""
        return self.create_company(**config)
    
    def create_exchange_from_config(self, config: Dict[str, Any]) -> Exchange:
        """Create an Exchange from configuration."""
        return self.create_exchange(**config)
    
    def create_company_share_from_config(self, config: Dict[str, Any]) -> CompanyShare:
        """Create a CompanyShare from configuration."""
        return self.create_company_share(**config)
    
    def create_currency_from_config(self, config: Dict[str, Any]) -> Currency:
        """Create a Currency from configuration."""
        return self.create_currency(**config)
    
    def create_crypto_from_config(self, config: Dict[str, Any]) -> Crypto:
        """Create a Crypto from configuration."""
        return self.create_crypto(**config)
    
    def create_commodity_from_config(self, config: Dict[str, Any]) -> Commodity:
        """Create a Commodity from configuration."""
        return self.create_commodity(**config)
    
    def create_bond_from_config(self, config: Dict[str, Any]) -> Bond:
        """Create a Bond from configuration."""
        # Convert date strings to date objects if needed
        if 'maturity_date' in config and isinstance(config['maturity_date'], str):
            config['maturity_date'] = datetime.strptime(config['maturity_date'], '%Y-%m-%d').date()
        return self.create_bond(**config)
    
    def create_etf_share_from_config(self, config: Dict[str, Any]) -> ETFShare:
        """Create an ETFShare from configuration."""
        # Convert date strings to date objects if needed
        if 'inception_date' in config and isinstance(config['inception_date'], str):
            config['inception_date'] = datetime.strptime(config['inception_date'], '%Y-%m-%d').date()
        return self.create_etf_share(**config)
    
    def create_future_from_config(self, config: Dict[str, Any]) -> Future:
        """Create a Future from configuration."""
        # Convert date strings to date objects if needed
        if 'expiry_date' in config and isinstance(config['expiry_date'], str):
            config['expiry_date'] = datetime.strptime(config['expiry_date'], '%Y-%m-%d').date()
        return self.create_future(**config)
    
    def create_option_from_config(self, config: Dict[str, Any]) -> Option:
        """Create an Option from configuration."""
        # Convert date strings to date objects if needed
        if 'expiry_date' in config and isinstance(config['expiry_date'], str):
            config['expiry_date'] = datetime.strptime(config['expiry_date'], '%Y-%m-%d').date()
        return self.create_option(**config)
    
    def create_index_from_config(self, config: Dict[str, Any]) -> Index:
        """Create an Index from configuration."""
        # Convert date strings to date objects if needed
        if 'base_date' in config and isinstance(config['base_date'], str):
            config['base_date'] = datetime.strptime(config['base_date'], '%Y-%m-%d').date()
        return self.create_index(**config)
    
    def create_financial_asset_from_config(self, config: Dict[str, Any]) -> FinancialAsset:
        """Create a FinancialAsset from configuration."""
        return self.create_financial_asset(**config)
    
    def _init_repositories(self):
        """Initialize database repositories using DatabaseService."""
        # Use the shared database service session for all repositories
        session = self.database_service.session
        
        # Initialize existing repositories
        self.company_share_repository = CompanyShareRepository(session)
        self.currency_repository = CurrencyRepository(session) if hasattr(CurrencyRepository, '__init__') else None
        self.bond_repository = BondRepository(session) if hasattr(BondRepository, '__init__') else None
        
    # Persistence Methods for CompanyShare
    def persist_company_share(self, company_share: CompanyShare) -> Optional[CompanyShare]:
        """
        Persist a company share entity to the database.
        
        Args:
            company_share: CompanyShare entity to persist
            
        Returns:
            Persisted company share entity or None if failed
        """
        try:
            return self.company_share_repository.add(company_share)
        except Exception as e:
            print(f"Error persisting company share {company_share.symbol if hasattr(company_share, 'symbol') else 'unknown'}: {str(e)}")
            return None
    
    def persist_currency(self, currency: Currency) -> Optional[Currency]:
        """
        Persist a currency entity to the database.
        
        Args:
            currency: Currency entity to persist
            
        Returns:
            Persisted currency entity or None if failed
        """
        try:
            if self.currency_repository:
                return self.currency_repository.add(currency)
            else:
                print("Currency repository not available")
                return None
        except Exception as e:
            print(f"Error persisting currency {currency.code if hasattr(currency, 'code') else 'unknown'}: {str(e)}")
            return None
    
    def persist_bond(self, bond: Bond) -> Optional[Bond]:
        """
        Persist a bond entity to the database.
        
        Args:
            bond: Bond entity to persist
            
        Returns:
            Persisted bond entity or None if failed
        """
        try:
            if self.bond_repository:
                return self.bond_repository.add(bond)
            else:
                print("Bond repository not available")
                return None
        except Exception as e:
            print(f"Error persisting bond {bond.symbol if hasattr(bond, 'symbol') else 'unknown'}: {str(e)}")
            return None
    
    # Pull Methods for CompanyShare
    def pull_company_share_by_id(self, share_id: int) -> Optional[CompanyShare]:
        """Pull company share by ID from database."""
        try:
            return self.company_share_repository.get_by_id(share_id)
        except Exception as e:
            print(f"Error pulling company share by ID {share_id}: {str(e)}")
            return None
    
    def pull_company_share_by_ticker(self, ticker: str) -> Optional[CompanyShare]:
        """Pull company share by ticker from database."""
        try:
            shares = self.company_share_repository.get_by_ticker(ticker)
            return shares[0] if shares else None
        except Exception as e:
            print(f"Error pulling company share by ticker {ticker}: {str(e)}")
            return None
    
    def pull_all_company_shares(self) -> List[CompanyShare]:
        """Pull all company shares from database."""
        try:
            return self.company_share_repository.get_all()
        except Exception as e:
            print(f"Error pulling all company shares: {str(e)}")
            return []
    
    def pull_currency_by_id(self, currency_id: int) -> Optional[Currency]:
        """Pull currency by ID from database."""
        try:
            if self.currency_repository:
                return self.currency_repository.get_by_id(currency_id)
            else:
                print("Currency repository not available")
                return None
        except Exception as e:
            print(f"Error pulling currency by ID {currency_id}: {str(e)}")
            return None
    
    def pull_bond_by_id(self, bond_id: int) -> Optional[Bond]:
        """Pull bond by ID from database."""
        try:
            if self.bond_repository:
                return self.bond_repository.get_by_id(bond_id)
            else:
                print("Bond repository not available")
                return None
        except Exception as e:
            print(f"Error pulling bond by ID {bond_id}: {str(e)}")
            return None
    
    # Generic persistence methods for entities without specific repositories
    def persist_company(self, company: Company) -> Optional[Company]:
        """
        Persist a company entity to the database.
        Note: This is a placeholder implementation - add specific repository when available.
        
        Args:
            company: Company entity to persist
            
        Returns:
            Persisted company entity or None if failed
        """
        try:
            # For now, just return the entity as-is since there's no specific repository
            # In a full implementation, you would add a CompanyRepository
            print(f"Warning: Company persistence not yet implemented for {company.name}")
            return company
        except Exception as e:
            print(f"Error persisting company {company.name}: {str(e)}")
            return None
    
    def persist_exchange(self, exchange: Exchange) -> Optional[Exchange]:
        """
        Persist an exchange entity to the database.
        Note: This is a placeholder implementation - add specific repository when available.
        
        Args:
            exchange: Exchange entity to persist
            
        Returns:
            Persisted exchange entity or None if failed
        """
        try:
            # For now, just return the entity as-is since there's no specific repository
            # In a full implementation, you would add an ExchangeRepository
            print(f"Warning: Exchange persistence not yet implemented for {exchange.name}")
            return exchange
        except Exception as e:
            print(f"Error persisting exchange {exchange.name}: {str(e)}")
            return None
    
    # Additional placeholder methods for other financial assets
    def persist_crypto(self, crypto: Crypto) -> Optional[Crypto]:
        """Persist a crypto entity to the database."""
        try:
            print(f"Warning: Crypto persistence not yet implemented for {crypto.symbol if hasattr(crypto, 'symbol') else 'unknown'}")
            return crypto
        except Exception as e:
            print(f"Error persisting crypto: {str(e)}")
            return None
    
    def persist_commodity(self, commodity: Commodity) -> Optional[Commodity]:
        """Persist a commodity entity to the database."""
        try:
            print(f"Warning: Commodity persistence not yet implemented for {commodity.symbol if hasattr(commodity, 'symbol') else 'unknown'}")
            return commodity
        except Exception as e:
            print(f"Error persisting commodity: {str(e)}")
            return None
    
    def persist_etf_share(self, etf_share: ETFShare) -> Optional[ETFShare]:
        """Persist an ETF share entity to the database."""
        try:
            print(f"Warning: ETF share persistence not yet implemented for {etf_share.symbol if hasattr(etf_share, 'symbol') else 'unknown'}")
            return etf_share
        except Exception as e:
            print(f"Error persisting ETF share: {str(e)}")
            return None
    
    def persist_future(self, future: Future) -> Optional[Future]:
        """Persist a future entity to the database."""
        try:
            print(f"Warning: Future persistence not yet implemented for {future.symbol if hasattr(future, 'symbol') else 'unknown'}")
            return future
        except Exception as e:
            print(f"Error persisting future: {str(e)}")
            return None
    
    def persist_option(self, option: Option) -> Optional[Option]:
        """Persist an option entity to the database."""
        try:
            print(f"Warning: Option persistence not yet implemented for {option.symbol if hasattr(option, 'symbol') else 'unknown'}")
            return option
        except Exception as e:
            print(f"Error persisting option: {str(e)}")
            return None